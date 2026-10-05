"""Durable Product ownership tests for PackageRuntime binding actions."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

import cyrene_reactor_product.package_runtime_owner as owner_module
from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.package_runtime_owner import (
    PACKAGE_RUNTIME_PACKAGE_ID,
    PackageRuntimeOwner,
    PackageRuntimeOwnerFailure,
)
from cyrene_reactor_product.store import ReactorStore

_BINDING = "reactor.vllm-import.primary"
_INSTALLATION = "install-real-123"
_REQUEST = "stable-request-123"
_TOKEN = "reactor-control-token-000000000000000000"


@dataclass(frozen=True)
class _Scope:
    binding_id: str
    package_id: str
    installation_id: str
    operation: str


@dataclass(frozen=True)
class _Receipt:
    request_id: str
    source_id: str
    protocol_version: str
    catalog_generation: int
    scope: _Scope
    operation_token: str
    gate_generation: int
    already_in_flight: bool
    already_completed: bool


def _receipt(request_id: str = _REQUEST, *, already_in_flight: bool = True) -> _Receipt:
    return _Receipt(
        request_id,
        "cyrene-reactor",
        "cyrene.runtime-maintenance.binding-operations.v1",
        7,
        _Scope(_BINDING, PACKAGE_RUNTIME_PACKAGE_ID, _INSTALLATION, "activate"),
        "private-operation-token-should-never-escape",
        4,
        already_in_flight,
        False,
    )


class _Client:
    source_id = "cyrene-reactor"

    def __init__(self, *, fail_after_intent: bool = False) -> None:
        self.calls: list[str] = []
        self.fail_after_intent = fail_after_intent
        self.store: ReactorStore | None = None

    def activate_and_persist(
        self, binding_id: str, installation_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        kwargs["persist_intent"](
            kwargs["request_id"],
            _Scope(binding_id, PACKAGE_RUNTIME_PACKAGE_ID, installation_id, "activate"),
        )
        assert self.store is not None
        intent = self.store.package_runtime_operation(kwargs["request_id"])
        assert intent is not None and intent["phase"] == "INTENT"
        self.calls.append("activate")
        if self.fail_after_intent:
            raise RuntimeError("transport failed with operation_token=must-not-leak")
        kwargs["persist"](_runtime_status(), _receipt(kwargs["request_id"]))
        self.calls.append("complete")
        return _runtime_status()

    def reconcile_binding_operation_and_persist(self, receipt: Any, *, reconcile: Any) -> None:
        self.calls.append("reconcile")
        reconcile(_runtime_status(), _installation(), receipt)
        self.calls.append("complete")


def _runtime_status() -> dict[str, Any]:
    return {
        "binding_id": _BINDING,
        "installation_id": _INSTALLATION,
        "generation": 9,
        "state": "RUNNING",
        "connection_ref": "cyrene-http-v1://127.0.0.1:19301",
    }


def _installation() -> dict[str, Any]:
    return {
        "installation_id": _INSTALLATION,
        "package_id": PACKAGE_RUNTIME_PACKAGE_ID,
        "state": "INSTALLED",
    }


def _owner(path: Path, client: _Client) -> tuple[ReactorStore, PackageRuntimeOwner]:
    store = ReactorStore(path)
    client.store = store
    return store, PackageRuntimeOwner(store, client, _BINDING)


def test_activate_persists_intent_then_private_outcome_and_exact_replay_is_read_only(
    tmp_path: Path,
) -> None:
    client = _Client()
    store, owner = _owner(tmp_path / "product.sqlite3", client)
    try:
        state = owner.activate(_REQUEST, _INSTALLATION)
        assert state == {
            "bindingId": _BINDING,
            "requestId": _REQUEST,
            "installationId": _INSTALLATION,
            "phase": "COMPLETED",
            "blocked": False,
            "runtimeState": "RUNNING",
        }
        assert client.calls == ["activate", "complete"]
        row = store.package_runtime_operation(_REQUEST)
        assert row is not None and row["receipt"]["operation_token"]
        assert stat_mode(store, tmp_path / "product.sqlite3") == 0o600
        assert owner.activate(_REQUEST, _INSTALLATION) == state
        assert client.calls == ["activate", "complete"]
        with pytest.raises(PackageRuntimeOwnerFailure, match="SCOPE_CONFLICT"):
            owner.activate(_REQUEST, "different-installation")
    finally:
        store.close()


def test_one_pending_request_per_binding(tmp_path: Path) -> None:
    client = _Client()
    store, owner = _owner(tmp_path / "product.sqlite3", client)
    try:
        store.create_package_runtime_intent(
            _REQUEST, _BINDING, PACKAGE_RUNTIME_PACKAGE_ID, _INSTALLATION
        )
        with pytest.raises(PackageRuntimeOwnerFailure, match="OPERATION_PENDING"):
            owner.activate("another-request", _INSTALLATION)
        assert client.calls == []
    finally:
        store.close()


def stat_mode(store: ReactorStore, path: Path) -> int:
    del store
    return path.stat().st_mode & 0o777


def test_partial_activation_is_unknown_and_never_replayed(tmp_path: Path) -> None:
    client = _Client(fail_after_intent=True)
    store, owner = _owner(tmp_path / "product.sqlite3", client)
    try:
        with pytest.raises(PackageRuntimeOwnerFailure, match="ACTIVATION_FAILED"):
            owner.activate(_REQUEST, _INSTALLATION)
        assert owner.status()["phase"] == "UNKNOWN"
        with pytest.raises(PackageRuntimeOwnerFailure, match="OUTCOME_UNKNOWN"):
            owner.activate(_REQUEST, _INSTALLATION)
        with pytest.raises(PackageRuntimeOwnerFailure, match="OUTCOME_UNKNOWN"):
            owner.reconcile(_REQUEST)
        assert client.calls == ["activate"]
    finally:
        store.close()


def test_unfinished_intent_is_promoted_to_unknown_on_status_read(tmp_path: Path) -> None:
    client = _Client()
    store, owner = _owner(tmp_path / "product.sqlite3", client)
    try:
        store.create_package_runtime_intent(
            _REQUEST, _BINDING, PACKAGE_RUNTIME_PACKAGE_ID, _INSTALLATION
        )
        assert owner.status()["phase"] == "UNKNOWN"
        assert store.package_runtime_operation(_REQUEST)["phase"] == "UNKNOWN"
        assert client.calls == []
    finally:
        store.close()


def test_malformed_optional_pending_receipt_is_redacted_and_stays_fail_closed(
    capsys: Any,
) -> None:
    class MalformedReceipt:
        operation_token = "do-not-log-this-secret"

    error = SimpleNamespace(pending_binding_operation=MalformedReceipt())
    result = owner_module._pending_receipt_document(
        error,
        request_id=_REQUEST,
        source_id="cyrene-reactor",
        binding_id=_BINDING,
        installation_id=_INSTALLATION,
    )
    log = capsys.readouterr().err

    assert result is None
    assert "PACKAGE_RUNTIME_PENDING_RECEIPT_INVALID" in log
    assert "do-not-log-this-secret" not in log
    assert "operation_token" not in log


@pytest.mark.parametrize("already_in_flight", [False, True])
def test_real_sdk_typed_pending_receipt_is_saved_and_reconciled_without_activate_replay(
    tmp_path: Path, already_in_flight: bool
) -> None:
    """Exercise SDK activation, lost replies, receipt restore, and reconcile end to end."""

    try:
        sdk = import_module("cyrene_runtime_maintenance")
    except ImportError:
        pytest.skip("PackageRuntime SDK source is supplied to this verification via PYTHONPATH")

    request_scope = sdk.BindingOperationScope(
        _BINDING, PACKAGE_RUNTIME_PACKAGE_ID, _INSTALLATION, "activate"
    )
    sdk_receipt = sdk.BindingOperationReceipt(
        request_id=_REQUEST,
        source_id="cyrene-reactor",
        protocol_version="cyrene.runtime-maintenance.binding-operations.v1",
        catalog_generation=7,
        scope=request_scope,
        operation_token="real-sdk-private-token-never-output",
        gate_generation=4,
        already_in_flight=already_in_flight,
        already_completed=False,
    )
    source_token = "source-secret-for-sdk-test-not-output"
    sdk_client = sdk.PackageRuntimeClient(
        "/tmp/cyrene-package-runtime-test.sock",
        source_id="cyrene-reactor",
        source_token=source_token,
        catalog_generation=7,
    )
    sdk_client._authority_capabilities = frozenset(
        {"cy-package-runtime.binding-operation-admission.v1"}
    )
    sdk_client._authority_checked = True

    def authority() -> dict[str, Any]:
        sdk_client._catalog_generation = 7
        sdk_client._authority_checked = True
        return {
            "catalog_generation": 7,
            "capabilities": ["cy-package-runtime.binding-operation-admission.v1"],
        }

    sdk_client.authority = authority
    sdk_client.runtime_status = lambda _binding_id: {
        **_runtime_status(),
        "failure_code": None,
        "failure_message": None,
    }
    sdk_client.get_installation = lambda _installation_id: _installation()

    completed: list[Any] = []
    raw_complete_calls: list[Any] = []

    def complete_after_owner_commit(receipt: Any, *, allow_in_flight: bool) -> dict[str, str]:
        raw_complete_calls.append(receipt)
        if not allow_in_flight:
            raise sdk.MaintenanceError("COMPLETE_REPLY_LOST", "test reply loss")
        completed.append(receipt)
        return {"status": "completed"}

    sdk_client._get_maintenance_client = lambda _generation: SimpleNamespace(
        _complete_binding_operation_after_owner_commit=complete_after_owner_commit
    )
    exchange_calls: list[str] = []

    def exchange(
        request: dict[str, Any], *, secrets: tuple[str, ...], expected_scope: Any = None
    ) -> dict[str, Any]:
        del secrets
        assert expected_scope == request_scope
        exchange_calls.append(request["operation"])
        return {
            **_runtime_status(),
            "failure_code": None,
            "failure_message": None,
            "binding_operation": owner_module._receipt_to_private_document(sdk_receipt),
        }

    sdk_client._exchange = exchange
    store = ReactorStore(tmp_path / "product.sqlite3")
    owner = PackageRuntimeOwner(store, sdk_client, _BINDING)
    try:
        expected_error = "BINDING_OPERATION_PENDING" if already_in_flight else "COMPLETE_REPLY_LOST"
        with pytest.raises(PackageRuntimeOwnerFailure, match=expected_error):
            owner.activate(_REQUEST, _INSTALLATION)
        pending = store.package_runtime_operation(_REQUEST)
        assert pending is not None and pending["phase"] == "RECEIPT_PENDING"
        assert pending["receipt"] == owner_module._receipt_to_private_document(sdk_receipt)
        assert exchange_calls == ["activate"]
        assert len(raw_complete_calls) == (0 if already_in_flight else 1)
        assert owner.reconcile(_REQUEST)["phase"] == "COMPLETED"
        assert len(completed) == 1
        assert completed[0] == sdk_receipt
        assert completed[0].already_in_flight is already_in_flight
        assert completed[0].already_completed is False
        assert len(raw_complete_calls) == (1 if already_in_flight else 2)
        assert exchange_calls == ["activate"]
    finally:
        store.close()


def test_saved_receipt_reconciles_actual_state_then_marks_complete(
    tmp_path: Path, monkeypatch: Any
) -> None:
    client = _Client()
    store, owner = _owner(tmp_path / "product.sqlite3", client)
    monkeypatch.setattr(
        owner_module, "_receipt_from_private_document", lambda _document: _receipt()
    )
    try:
        store.create_package_runtime_intent(
            _REQUEST, _BINDING, PACKAGE_RUNTIME_PACKAGE_ID, _INSTALLATION
        )
        store.commit_package_runtime_outcome(
            _REQUEST, _runtime_status(), owner_module._receipt_to_private_document(_receipt())
        )
        assert owner.reconcile(_REQUEST)["phase"] == "COMPLETED"
        assert client.calls == ["reconcile", "complete"]
    finally:
        store.close()


def test_reconcile_refuses_mismatched_actual_state_and_keeps_pending(
    tmp_path: Path, monkeypatch: Any
) -> None:
    client = _Client()
    store, owner = _owner(tmp_path / "product.sqlite3", client)
    monkeypatch.setattr(
        owner_module, "_receipt_from_private_document", lambda _document: _receipt()
    )
    client.reconcile_binding_operation_and_persist = lambda receipt, *, reconcile: reconcile(
        {**_runtime_status(), "state": "STOPPED"}, _installation(), receipt
    )
    try:
        store.create_package_runtime_intent(
            _REQUEST, _BINDING, PACKAGE_RUNTIME_PACKAGE_ID, _INSTALLATION
        )
        store.commit_package_runtime_outcome(
            _REQUEST, _runtime_status(), owner_module._receipt_to_private_document(_receipt())
        )
        with pytest.raises(PackageRuntimeOwnerFailure, match="ACTUAL_STATE_MISMATCH"):
            owner.reconcile(_REQUEST)
        assert owner.status()["phase"] == "RECEIPT_PENDING"
    finally:
        store.close()


def test_api_requires_real_bearer_even_in_unauthenticated_dev_and_rejects_forged_body(
    tmp_path: Path,
) -> None:
    credential = tmp_path / "control.token"
    credential.write_text(_TOKEN, encoding="utf-8")
    credential.chmod(0o600)
    store = ReactorStore(tmp_path / "product.sqlite3")
    sdk_client = _Client()
    sdk_client.store = store
    owner = PackageRuntimeOwner(store, sdk_client, _BINDING)
    app = create_app(
        database_path=tmp_path / "api.sqlite3",
        credential_file=credential,
        package_runtime_owner=owner,
        allow_unauthenticated_dev=True,
    )
    try:
        with TestClient(app) as client:
            path = f"/api/v1/runtime-bindings/{_BINDING}"
            assert client.get(path).status_code == 403
            assert (
                client.get(path, headers={"Authorization": f"Bearer {_TOKEN}"}).status_code == 200
            )
            headers = {"Authorization": f"Bearer {_TOKEN}", "Idempotency-Key": _REQUEST}
            bad = client.post(
                path + "/actions/activate",
                headers=headers,
                json={"installationId": _INSTALLATION, "receipt": {"operation_token": "forged"}},
            )
            assert bad.status_code == 422
            forged_reconcile = client.post(
                path + "/actions/reconcile",
                headers=headers,
                json={"operation_token": "forged"},
            )
            assert forged_reconcile.status_code == 422
            good = client.post(
                path + "/actions/activate",
                headers=headers,
                json={"installationId": _INSTALLATION},
            )
            assert good.status_code == 200
            assert "private-operation-token" not in good.text
            assert "connection_ref" not in good.text
            assert "operation_token" not in good.text
    finally:
        store.close()


def test_missing_control_credential_fails_closed_even_in_dev(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "product.sqlite3", allow_unauthenticated_dev=True)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/runtime-bindings/{_BINDING}")
    assert response.status_code == 503
