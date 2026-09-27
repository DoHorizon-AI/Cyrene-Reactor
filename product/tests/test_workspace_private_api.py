"""
┌─────────────────────────────────────────────────────────────────────┐
│  Module: tests.test_workspace_private_api                            │
│  Role: Scoped Reactor private API and legacy read isolation.        │
│  模块职责：验证私有服务身份、ModelImport 范围和旧路由读取隔离。          │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from test_product_mvp import _TestServingExecutionPort

from cyrene_reactor_product import create_app
from cyrene_reactor_product.domain import (
    CreateModelImportRequest,
    ModelImport,
    ModelImportSource,
    ModelImportSourceKind,
    ModelImportState,
    utc_now,
)
from cyrene_reactor_product.store import ReactorStore
from cyrene_reactor_product.workspace_auth import (
    WorkspaceServiceAuthenticator,
    WorkspaceServingBindingGrantSet,
)

COMMIT = "5fee7c4ed634dc66c6e318c8ac2897b8b9154536"


def _credential_map(*entries: tuple[str, str, str]) -> str:
    return json.dumps(
        {
            "version": 1,
            "credentials": [
                {
                    "tokenSha256": hashlib.sha256(token.encode("ascii")).hexdigest(),
                    "organizationId": organization_id,
                    "workspaceId": workspace_id,
                }
                for token, organization_id, workspace_id in entries
            ],
        }
    )


def _grant_map(*entries: tuple[str, str, str]) -> str:
    return json.dumps(
        {
            "version": 1,
            "grants": [
                {
                    "servingBindingId": binding_id,
                    "organizationId": organization_id,
                    "workspaceId": workspace_id,
                }
                for binding_id, organization_id, workspace_id in entries
            ],
        }
    )


def _command(
    name: str = "scoped model", binding_id: str = "local-process-serving"
) -> dict[str, object]:
    return {
        "name": name,
        "servingBindingId": binding_id,
        "source": {
            "kind": "HUGGING_FACE",
            "repository": "Qwen/Qwen2.5-1.5B-Instruct",
            "revision": COMMIT,
        },
    }


class _ImportCountingExecutionPort(_TestServingExecutionPort):
    def __init__(self):
        super().__init__()
        self.import_count = 0

    def import_model(self, command):
        self.import_count += 1
        return super().import_model(command)


def test_workspace_auth_is_fail_closed_even_when_legacy_dev_mode_is_explicit(
    tmp_path: Path, capsys
):
    token = "reactor-workspace-service-" + "a" * 16
    engine = _ImportCountingExecutionPort()
    app = create_app(
        database_path=tmp_path / "reactor.sqlite3",
        engine=engine,
        allow_unauthenticated_dev=True,
    )
    try:
        with TestClient(app) as client:
            assert client.get("/healthz").status_code == 200
            legacy = client.get("/api/v1/model-imports")
            assert legacy.status_code == 200
            missing_private = client.get("/internal/workspace/v1/model-imports")
            assert missing_private.status_code == 503
            unauthorized = client.get(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + "x" * 31},
            )
            assert unauthorized.status_code == 503  # no configured map takes precedence
            assert token not in unauthorized.text
    finally:
        app.state.reactor_store.close()

    configured = create_app(
        database_path=tmp_path / "configured.sqlite3",
        workspace_credential_map_json=_credential_map((token, "org-one", "workspace-one")),
    )
    try:
        with TestClient(configured) as client:
            unauthorized = client.get(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + "x" * 32},
            )
            assert unauthorized.status_code == 401
            assert token not in unauthorized.text
            ungranted = client.post(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + token, "Idempotency-Key": "no-grant"},
                json=_command(),
            )
            assert ungranted.status_code == 403
            assert ungranted.json()["code"] == "REACTOR_WORKSPACE_BINDING_NOT_GRANTED"
            assert (
                configured.state.reactor_store._connection.execute(
                    "SELECT COUNT(*) FROM model_imports"
                ).fetchone()[0]
                == 0
            )
            assert (
                configured.state.reactor_store._connection.execute(
                    "SELECT COUNT(*) FROM idempotency"
                ).fetchone()[0]
                == 0
            )
    finally:
        configured.state.reactor_store.close()

    production_app = create_app(database_path=tmp_path / "production.sqlite3")
    try:
        with TestClient(production_app) as client:
            assert client.get("/healthz").status_code == 200
            rejected_read = client.get("/api/v1/model-imports")
            assert rejected_read.status_code == 503
            assert rejected_read.json()["code"] == "REACTOR_CONTROL_AUTH_UNAVAILABLE"
            assert client.get("/api/v1/deployments").status_code == 503
            rejected_write = client.post("/api/v1/model-imports", json=_command())
            assert rejected_write.status_code == 503
            assert (
                production_app.state.reactor_engine.__class__.__name__
                == "UnconfiguredServingExecutionPort"
            )
            assert client.get("/internal/workspace/v1/model-imports").status_code == 503
    finally:
        production_app.state.reactor_store.close()

    private_only_app = create_app(
        database_path=tmp_path / "private-only.sqlite3",
        workspace_credential_map_json=_credential_map((token, "org-one", "workspace-one")),
    )
    try:
        with TestClient(private_only_app) as client:
            private_list = client.get(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + token},
            )
            assert private_list.status_code == 200
            assert private_list.json() == []
            assert client.get("/api/v1/model-imports").status_code == 503
    finally:
        private_only_app.state.reactor_store.close()

    captured = capsys.readouterr()
    assert token not in captured.out
    assert token not in captured.err


def test_control_bearer_remains_separate_from_workspace_auth(tmp_path: Path):
    token_path = tmp_path / "control.token"
    token = "reactor-control-service-" + "z" * 20
    token_path.write_text(token)
    token_path.chmod(0o600)
    app = create_app(
        database_path=tmp_path / "reactor.sqlite3",
        credential_file=token_path,
        allow_unauthenticated_dev=True,
    )
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/model-imports").status_code == 403
            legacy = client.get(
                "/api/v1/model-imports",
                headers={"Authorization": "Bearer " + token},
            )
            assert legacy.status_code == 200
            assert (
                client.get(
                    "/internal/workspace/v1/model-imports",
                    headers={"Authorization": "Bearer " + token},
                ).status_code
                == 503
            )
    finally:
        app.state.reactor_store.close()


def test_scoped_imports_are_atomic_and_hidden_from_legacy_model_and_control_reads(
    tmp_path: Path, capsys
):
    token = "reactor-workspace-service-" + "a" * 16
    rotated = "reactor-workspace-service-" + "b" * 16
    other = "reactor-workspace-service-" + "c" * 16
    control_credential = tmp_path / "control.token"
    control_token = "reactor-control-service-" + "y" * 20
    control_credential.write_text(control_token)
    control_credential.chmod(0o600)
    control_headers = {"Authorization": "Bearer " + control_token}
    engine = _ImportCountingExecutionPort()
    app = create_app(
        database_path=tmp_path / "reactor.sqlite3",
        credential_file=control_credential,
        engine=engine,
        engines={
            "legacy-local-serving": engine,
            "shared-serving": engine,
            "workspace-one-only": engine,
            "historical-serving": engine,
        },
        workspace_credential_map_json=_credential_map(
            (token, "org-one", "workspace-one"),
            (rotated, "org-one", "workspace-one"),
            (other, "org-two", "workspace-two"),
        ),
        workspace_serving_binding_grants_json=_grant_map(
            ("shared-serving", "org-one", "workspace-one"),
            ("workspace-one-only", "org-one", "workspace-one"),
            ("shared-serving", "org-two", "workspace-two"),
        ),
    )
    try:
        with TestClient(app) as client:
            key = "same-idempotency-key"
            created = client.post(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + token, "Idempotency-Key": key},
                json=_command(binding_id="shared-serving"),
            )
            assert created.status_code == 201, created.text
            first = created.json()
            assert first["state"] == "READY"
            first_id = first["id"]
            assert app.state.reactor_store.model_import_scope(UUID(first_id)) == (
                "org-one",
                "workspace-one",
            )
            assert engine.import_count == 1

            replay = client.post(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + rotated, "Idempotency-Key": key},
                json=_command(binding_id="shared-serving"),
            )
            assert replay.status_code == 201
            assert replay.json()["id"] == first_id
            assert engine.import_count == 1

            first_scope_list = client.get(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + rotated},
            )
            assert [item["id"] for item in first_scope_list.json()] == [first_id]
            other_scope_list = client.get(
                "/internal/workspace/v1/model-imports", headers={"Authorization": "Bearer " + other}
            )
            assert other_scope_list.json() == []
            assert (
                client.get(
                    "/internal/workspace/v1/model-imports",
                    headers=control_headers,
                ).status_code
                == 401
            )

            workspace_one_binding = client.post(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + token, "Idempotency-Key": "workspace-one"},
                json=_command(binding_id="workspace-one-only"),
            )
            assert workspace_one_binding.status_code == 201
            workspace_one_binding_id = workspace_one_binding.json()["id"]
            assert engine.import_count == 2

            cross_workspace_binding = client.post(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + other, "Idempotency-Key": "cross-binding"},
                json=_command(binding_id="workspace-one-only"),
            )
            assert cross_workspace_binding.status_code == 403
            assert cross_workspace_binding.json()["code"] == "REACTOR_WORKSPACE_BINDING_NOT_GRANTED"
            assert engine.import_count == 2

            historical_binding = client.post(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + token, "Idempotency-Key": "old-binding"},
                json=_command(binding_id="historical-serving"),
            )
            assert historical_binding.status_code == 403
            assert engine.import_count == 2

            second_scope = client.post(
                "/internal/workspace/v1/model-imports",
                headers={"Authorization": "Bearer " + other, "Idempotency-Key": key},
                json=_command(binding_id="shared-serving"),
            )
            assert second_scope.status_code == 201
            second_id = second_scope.json()["id"]
            assert second_id != first_id
            assert engine.import_count == 3
            assert app.state.reactor_store.model_import_scope(UUID(second_id)) == (
                "org-two",
                "workspace-two",
            )

            legacy = client.post(
                "/api/v1/model-imports",
                headers={**control_headers, "Idempotency-Key": key},
                json=_command("legacy model", "legacy-local-serving"),
            )
            assert legacy.status_code == 201
            legacy_id = legacy.json()["id"]
            assert app.state.reactor_store.model_import_scope(UUID(legacy_id)) is None

            legacy_list = client.get("/api/v1/model-imports", headers=control_headers)
            assert [item["id"] for item in legacy_list.json()] == [legacy_id]
            assert (
                client.get(
                    f"/api/v1/model-imports/{workspace_one_binding_id}",
                    headers=control_headers,
                ).status_code
                == 404
            )
            assert (
                client.get(f"/api/v1/model-imports/{first_id}", headers=control_headers).status_code
                == 404
            )
            assert (
                client.get(
                    f"/api/v1/model-imports/{second_id}", headers=control_headers
                ).status_code
                == 404
            )
            assert (
                client.get(
                    f"/api/v1/deployment-drafts/{first_id}",
                    headers=control_headers,
                ).status_code
                == 404
            )
            assert (
                client.get(f"/api/v1/deployments/{first_id}", headers=control_headers).status_code
                == 404
            )
            assert first_id not in {
                item["id"]
                for item in client.get("/api/v1/deployment-drafts", headers=control_headers).json()
            }
            assert first_id not in {
                item["id"]
                for item in client.get("/api/v1/deployments", headers=control_headers).json()
            }
    finally:
        app.state.reactor_store.close()

    captured = capsys.readouterr()
    for credential in (token, rotated, other, control_token):
        assert credential not in captured.out
        assert credential not in captured.err


def test_private_import_intent_scope_and_idempotency_rollback_together(tmp_path: Path):
    store = ReactorStore(tmp_path / "reactor.sqlite3")
    source = ModelImportSource(
        kind=ModelImportSourceKind.HUGGING_FACE,
        repository="Qwen/Qwen2.5-1.5B-Instruct",
        revision=COMMIT,
    )
    now = utc_now()
    pending = ModelImport(
        id=uuid4(),
        name="atomic import",
        serving_binding_id="local-process-serving",
        source=source,
        state=ModelImportState.VALIDATING,
        created_at=now,
        updated_at=now,
        resource_version=1,
    )
    command = CreateModelImportRequest(
        name=pending.name,
        serving_binding_id=pending.serving_binding_id,
        source=source,
    )
    digest = hashlib.sha256(
        command.model_dump_json(by_alias=True, exclude_none=True).encode()
    ).hexdigest()
    with store._connection:
        store._connection.execute(
            "CREATE TRIGGER reject_workspace_scope BEFORE INSERT ON model_import_scopes "
            "BEGIN SELECT RAISE(ABORT, 'scope insert rejected'); END"
        )

    with pytest.raises(sqlite3.IntegrityError, match="scope insert rejected"):
        store.commit_model_import_intent(
            pending,
            "atomic-key",
            digest,
            idempotency_scope="workspace:model-import:scope-hash",
            workspace_scope=("org-one", "workspace-one"),
            workspace_serving_binding_grants=frozenset(
                {("local-process-serving", "org-one", "workspace-one")}
            ),
        )

    assert store.get_model_import(pending.id) is None
    assert store.model_import_scope(pending.id) is None
    assert store._connection.execute("SELECT COUNT(*) FROM idempotency").fetchone()[0] == 0
    store.close()


def test_workspace_credential_map_rejects_duplicate_hash_and_bad_json():
    token = "reactor-workspace-service-" + "a" * 16
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    duplicate = json.dumps(
        {
            "version": 1,
            "credentials": [
                {
                    "tokenSha256": digest,
                    "organizationId": "org-one",
                    "workspaceId": "workspace-one",
                },
                {
                    "tokenSha256": digest,
                    "organizationId": "org-two",
                    "workspaceId": "workspace-two",
                },
            ],
        }
    )
    with pytest.raises(ValueError, match="REACTOR_WORKSPACE_CREDENTIAL_MAP_INVALID"):
        WorkspaceServiceAuthenticator(duplicate)
    with pytest.raises(ValueError, match="REACTOR_WORKSPACE_CREDENTIAL_MAP_INVALID"):
        WorkspaceServiceAuthenticator('{"version":1,"credentials":[')
    duplicate_grant = _grant_map(
        ("binding-one", "org-one", "workspace-one"),
        ("binding-one", "org-one", "workspace-one"),
    )
    with pytest.raises(ValueError, match="REACTOR_WORKSPACE_SERVING_BINDING_GRANTS_INVALID"):
        WorkspaceServingBindingGrantSet(duplicate_grant)
