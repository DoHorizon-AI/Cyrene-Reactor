"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 package_runtime_owner.py                                         │
│  Module: cyrene_reactor_product.package_runtime_owner                │
│  Role: Own PackageRuntime binding lifecycle and endpoint admission.  │
│                                                                      │
│  模块职责：核验正式包运行回执并解析为本机 HTTP 服务端口。               │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import asdict
from importlib import import_module
from pathlib import Path
from threading import RLock
from typing import Any, Protocol, cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from cyrene_reactor_product.logging import emit_diagnostic_error
from cyrene_reactor_product.remote_engine import (
    RemoteServingExecutionPort,
    ServingBindingConfiguration,
)

PACKAGE_RUNTIME_PACKAGE_ID = "cyrene.serving.vllm-runtime"
PACKAGE_RUNTIME_CAPABILITY_ID = "execution.engine.v1"
PACKAGE_RUNTIME_INTERFACE_VERSION = "1"
PACKAGE_RUNTIME_HTTP_TRANSPORT = "http"
PACKAGE_RUNTIME_CONTROL_PROTOCOL = "cy-package-runtime.control.v1"
REACTOR_PACKAGE_RUNTIME_SOURCE_ID = "cyrene-reactor"

_BINDING_ID = re.compile(r"[A-Za-z0-9][a-z0-9_.-]{1,127}\Z")
_PACKAGE_VERSION = re.compile(r"[A-Za-z0-9.+-]{1,128}\Z")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


class PackageRuntimeBindingFailure(RuntimeError):
    """Block a configured package binding when trusted owner evidence is unavailable.

    中文:包运行绑定证据不可用或不匹配时阻止执行。
    """

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


class PackageRuntimeServingBindingConfiguration(BaseModel):
    """Owner-only credentials for one configured Product binding. | owner 私有绑定配置。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    credential_file: Path

    @field_validator("credential_file")
    @classmethod
    def _require_absolute_credential_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("credential_file must be absolute")
        return value


class PackageRuntimeClientProtocol(Protocol):
    """Type only the read methods admitted to the Reactor owner. | 仅声明只读接口。"""

    source_id: str | None
    catalog_generation: int | None

    def authority(self) -> Mapping[str, Any]: ...

    def runtime_status(self, binding_id: str) -> Mapping[str, Any]: ...

    def get_installation(self, installation_id: str) -> Mapping[str, Any]: ...

    def activate_and_persist(
        self,
        binding_id: str,
        installation_id: str,
        *,
        package_id: str,
        persist_intent: Any,
        persist: Any,
        request_id: str,
    ) -> Mapping[str, Any]: ...

    def reconcile_binding_operation_and_persist(self, receipt: Any, *, reconcile: Any) -> Any: ...


class PackageRuntimeOwnerFailure(RuntimeError):
    """Safe, stable lifecycle error suitable for a Product HTTP response."""

    def __init__(self, code: str, status: int = 409) -> None:
        self.code = code
        self.status = status
        super().__init__(code)


class PackageRuntimeOwner:
    """Narrow Product owner for one configured Reactor PackageRuntime binding."""

    def __init__(self, store: Any, client: PackageRuntimeClientProtocol, binding_id: str) -> None:
        if not isinstance(binding_id, str) or not _BINDING_ID.fullmatch(binding_id):
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_BINDING_NOT_CONFIGURED", 503)
        if getattr(client, "source_id", None) != REACTOR_PACKAGE_RUNTIME_SOURCE_ID:
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_SOURCE_MISMATCH", 503)
        self.store = store
        self.client = client
        self.binding_id = binding_id
        self._operation_lock = RLock()

    def activate(self, request_id: str, installation_id: str) -> dict[str, Any]:
        """Activate once after durable intent; retries return state or require reconcile."""

        with self._operation_lock:
            return self._activate_locked(request_id, installation_id)

    def _activate_locked(self, request_id: str, installation_id: str) -> dict[str, Any]:

        if not isinstance(request_id, str) or not _is_safe_request_id(request_id):
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_REQUEST_ID_INVALID", 422)
        if not isinstance(installation_id, str) or not installation_id.strip():
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_INSTALLATION_ID_REQUIRED", 422)
        existing = self.store.package_runtime_operation(request_id)
        if existing is not None:
            self._check_scope(existing, installation_id)
            if existing["phase"] == "COMPLETED":
                return self._public_state(existing)
            if existing.get("receipt"):
                raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_RECONCILE_REQUIRED", 409)
            if existing["phase"] == "INTENT":
                self.store.mark_package_runtime_unknown(request_id)
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_OUTCOME_UNKNOWN", 409)

        pending = self.store.pending_package_runtime_operation(self.binding_id)
        if pending is not None:
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_BINDING_OPERATION_PENDING", 409)

        def persist_intent(actual_request_id: str, scope: Any) -> None:
            if actual_request_id != request_id or (
                scope.binding_id,
                scope.package_id,
                scope.installation_id,
                scope.operation,
            ) != (self.binding_id, PACKAGE_RUNTIME_PACKAGE_ID, installation_id, "activate"):
                raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_REQUEST_SCOPE_CONFLICT", 409)
            self.store.create_package_runtime_intent(
                request_id, self.binding_id, PACKAGE_RUNTIME_PACKAGE_ID, installation_id
            )
            return None

        def persist(runtime_status: Mapping[str, Any], receipt: Any) -> None:
            if not isinstance(runtime_status, Mapping):
                raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_OUTCOME_INVALID", 502)
            self._validate_actual(runtime_status, installation_id)
            self.store.commit_package_runtime_outcome(
                request_id,
                dict(runtime_status),
                _receipt_to_private_document(receipt),
            )

        try:
            self.client.activate_and_persist(
                self.binding_id,
                installation_id,
                package_id=PACKAGE_RUNTIME_PACKAGE_ID,
                persist_intent=persist_intent,
                persist=persist,
                request_id=request_id,
            )
            self.store.complete_package_runtime_operation(request_id)
        except PackageRuntimeOwnerFailure:
            raise
        except Exception as exc:
            current = self.store.package_runtime_operation(request_id)
            persisted_receipt = False
            if current is not None and current["phase"] == "INTENT":
                receipt_document = _pending_receipt_document(
                    exc,
                    request_id=request_id,
                    source_id=getattr(self.client, "source_id", None),
                    binding_id=self.binding_id,
                    installation_id=installation_id,
                )
                if receipt_document is not None:
                    self.store.persist_package_runtime_receipt(request_id, receipt_document)
                    persisted_receipt = True
                else:
                    self.store.mark_package_runtime_unknown(request_id)
            code = getattr(exc, "code", "PACKAGE_RUNTIME_ACTIVATION_FAILED")
            raise PackageRuntimeOwnerFailure(
                _safe_code(code), 409 if persisted_receipt else 502
            ) from None
        return self.status()

    def reconcile(self, request_id: str) -> dict[str, Any]:
        record = self.store.package_runtime_operation(request_id)
        if record is None:
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_REQUEST_NOT_FOUND", 404)
        self._check_scope(record, str(record["installation_id"]))
        receipt_data = record.get("receipt")
        if not isinstance(receipt_data, Mapping):
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_OUTCOME_UNKNOWN", 409)
        receipt = _receipt_from_private_document(receipt_data)

        def reconcile(
            runtime_status: Mapping[str, Any], installation: Mapping[str, Any], broker_receipt: Any
        ) -> None:
            if getattr(broker_receipt, "request_id", None) != request_id:
                raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_RECEIPT_SCOPE_MISMATCH", 409)
            scope = getattr(broker_receipt, "scope", None)
            if scope is None or (
                scope.binding_id,
                scope.package_id,
                scope.installation_id,
                scope.operation,
            ) != (
                self.binding_id,
                PACKAGE_RUNTIME_PACKAGE_ID,
                record["installation_id"],
                "activate",
            ):
                raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_RECEIPT_SCOPE_MISMATCH", 409)
            self._validate_actual(runtime_status, str(record["installation_id"]))
            previous_status = record.get("runtime_status")
            if isinstance(previous_status, Mapping) and runtime_status.get(
                "connection_ref"
            ) != previous_status.get("connection_ref"):
                raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_CONNECTION_REF_MISMATCH", 409)
            if (
                installation.get("installation_id") != record["installation_id"]
                or installation.get("package_id") != PACKAGE_RUNTIME_PACKAGE_ID
                or installation.get("state") != "INSTALLED"
            ):
                raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_INSTALLATION_MISMATCH", 409)
            self.store.commit_package_runtime_outcome(
                request_id, dict(runtime_status), _receipt_to_private_document(broker_receipt)
            )

        try:
            self.client.reconcile_binding_operation_and_persist(receipt, reconcile=reconcile)
            self.store.complete_package_runtime_operation(request_id)
        except PackageRuntimeOwnerFailure:
            raise
        except Exception as exc:
            code = getattr(exc, "code", "PACKAGE_RUNTIME_RECONCILIATION_FAILED")
            raise PackageRuntimeOwnerFailure(_safe_code(code), 409) from None
        return self.status()

    def status(self) -> dict[str, Any]:
        pending = self.store.pending_package_runtime_operation(self.binding_id)
        if pending is not None:
            if pending["phase"] == "INTENT" and not pending.get("receipt"):
                self.store.mark_package_runtime_unknown(str(pending["request_id"]))
                pending = self.store.package_runtime_operation(str(pending["request_id"]))
            if pending is None:
                return {"bindingId": self.binding_id, "phase": "UNKNOWN"}
            return self._public_state(pending)
        # Return the latest durable owner state, if any, without exposing receipt data.
        latest = self.store.latest_package_runtime_operation(self.binding_id)
        if latest is None:
            return {"bindingId": self.binding_id, "phase": "NOT_CONFIGURED"}
        return self._public_state(latest)

    def _validate_actual(self, status: Mapping[str, Any], installation_id: str) -> None:
        if (
            status.get("binding_id") != self.binding_id
            or status.get("installation_id") != installation_id
            or status.get("state") != "RUNNING"
            or not isinstance(status.get("connection_ref"), str)
            or not status.get("connection_ref")
        ):
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_ACTUAL_STATE_MISMATCH", 409)
        try:
            control_url_from_connection_ref(str(status["connection_ref"]))
        except PackageRuntimeBindingFailure as exc:
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_CONNECTION_REF_INVALID", 409) from exc

    def _check_scope(self, record: Mapping[str, Any], installation_id: str) -> None:
        if (
            record.get("binding_id") != self.binding_id
            or record.get("package_id") != PACKAGE_RUNTIME_PACKAGE_ID
            or record.get("installation_id") != installation_id
            or record.get("operation") != "activate"
        ):
            raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_REQUEST_SCOPE_CONFLICT", 409)

    def _public_state(self, record: Mapping[str, Any]) -> dict[str, Any]:
        status = record.get("runtime_status")
        return {
            "bindingId": self.binding_id,
            "requestId": record["request_id"],
            "installationId": record["installation_id"],
            "phase": record["phase"],
            "blocked": record["phase"] != "COMPLETED",
            "runtimeState": status.get("state") if isinstance(status, Mapping) else None,
        }


def package_runtime_owner_from_environment(store: Any) -> PackageRuntimeOwner | None:
    """Load the single configured source binding through the SDK environment."""

    binding_id = os.environ.get("REACTOR_PACKAGE_RUNTIME_BINDING_ID", "").strip()
    if not binding_id:
        return None
    configured_source = os.environ.get("CYRENE_RUNTIME_ACTIVITY_SOURCE_ID", "").strip()
    if configured_source != REACTOR_PACKAGE_RUNTIME_SOURCE_ID:
        raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_SOURCE_MISMATCH", 503)
    client = _runtime_client_from_environment()
    return PackageRuntimeOwner(store, client, binding_id)


def _is_safe_request_id(value: str) -> bool:
    return 1 <= len(value) <= 128 and all(ch.isalnum() or ch in "-_.:" for ch in value)


def _safe_code(value: object) -> str:
    text = str(value)
    return text if re.fullmatch(r"[A-Z0-9_]{1,96}", text) else "PACKAGE_RUNTIME_OPERATION_FAILED"


def _receipt_to_private_document(receipt: Any) -> dict[str, Any]:
    try:
        value = asdict(receipt)
    except Exception as exc:
        raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_RECEIPT_INVALID", 502) from exc
    if not isinstance(value, dict) or not isinstance(value.get("scope"), dict):
        raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_RECEIPT_INVALID", 502)
    return value


def _pending_receipt_document(
    error: Exception,
    *,
    request_id: str,
    source_id: object,
    binding_id: str,
    installation_id: str,
) -> dict[str, Any] | None:
    """Accept only the SDK's exact, typed pending receipt for this operation."""

    receipt = getattr(error, "pending_binding_operation", None)
    if receipt is None:
        return None
    try:
        document = _receipt_to_private_document(receipt)
        scope = document.get("scope")
        if not isinstance(scope, Mapping) or (
            document.get("request_id"),
            document.get("source_id"),
            scope.get("binding_id"),
            scope.get("package_id"),
            scope.get("installation_id"),
            scope.get("operation"),
        ) != (
            request_id,
            source_id,
            binding_id,
            PACKAGE_RUNTIME_PACKAGE_ID,
            installation_id,
            "activate",
        ):
            return None
        if (
            not isinstance(document.get("operation_token"), str)
            or not document["operation_token"]
            or type(document.get("already_in_flight")) is not bool
            or type(document.get("already_completed")) is not bool
            or document.get("already_completed")
            or type(document.get("catalog_generation")) is not int
            or document["catalog_generation"] <= 0
            or type(document.get("gate_generation")) is not int
            or document["gate_generation"] <= 0
            or document.get("protocol_version")
            != "cyrene.runtime-maintenance.binding-operations.v1"
        ):
            return None
        return document
    except (
        AttributeError,
        KeyError,
        PackageRuntimeOwnerFailure,
        TypeError,
        ValueError,
    ):
        emit_diagnostic_error(
            "product.package_runtime.pending_receipt_rejected",
            "PACKAGE_RUNTIME_PENDING_RECEIPT_INVALID",
            "The SDK pending receipt could not be validated; owner state remains fail-closed.",
        )
        return None


def _receipt_from_private_document(value: Mapping[str, Any]) -> Any:
    try:
        sdk = import_module("cyrene_runtime_maintenance")
        scope_type = sdk.BindingOperationScope
        receipt_type = sdk.BindingOperationReceipt
        scope_data = value["scope"]
        if not isinstance(scope_data, Mapping):
            raise TypeError
        return receipt_type(
            request_id=value["request_id"],
            source_id=value["source_id"],
            protocol_version=value["protocol_version"],
            catalog_generation=value["catalog_generation"],
            scope=scope_type(**dict(scope_data)),
            operation_token=value["operation_token"],
            gate_generation=value["gate_generation"],
            already_in_flight=value["already_in_flight"],
            already_completed=value["already_completed"],
        )
    except Exception as exc:
        raise PackageRuntimeOwnerFailure("PACKAGE_RUNTIME_RECEIPT_INVALID", 503) from exc


def control_url_from_connection_ref(connection_ref: str) -> str:
    """Decode only the canonical Plugin-owned IPv4 loopback HTTP reference.

    中文:仅解码规范的插件所有 IPv4 环回 HTTP 引用。
    """

    try:
        parsed = urlsplit(connection_ref)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_CONNECTION_REF_INVALID", "the receipt has an invalid HTTP reference"
        ) from exc
    if (
        parsed.scheme != "cyrene-http-v1"
        or parsed.hostname != "127.0.0.1"
        or port is None
        or not 1 <= port <= 65535
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or connection_ref != f"cyrene-http-v1://127.0.0.1:{port}"
    ):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_CONNECTION_REF_INVALID", "the receipt is not a canonical loopback ref"
        )
    return f"http://127.0.0.1:{port}"


def package_runtime_engine(
    binding_id: str,
    configuration: Mapping[str, Any],
    *,
    client: PackageRuntimeClientProtocol | None = None,
) -> RemoteServingExecutionPort:
    """Verify the current receipt and metadata before creating a serving port.

    The SDK performs source-authenticated, read-only PackageRuntime requests.
    Reactor checks the configured binding and returned installation identity,
    then admits only the signed package metadata exposed by that receipt's
    loopback endpoint. No package lifecycle operation is issued here.

    中文:通过 source 凭据只读查询并核验当前回执,再校验其环回端点元数据。
    """

    if not isinstance(binding_id, str) or not _BINDING_ID.fullmatch(binding_id):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_BINDING_ID_INVALID", "the configured binding id is invalid"
        )
    try:
        binding_configuration = PackageRuntimeServingBindingConfiguration.model_validate(
            configuration
        )
    except (TypeError, ValidationError) as exc:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_CONFIGURATION_INVALID", "the owner credential configuration is invalid"
        ) from exc

    runtime_client = client if client is not None else _runtime_client_from_environment()
    if getattr(runtime_client, "source_id", None) != REACTOR_PACKAGE_RUNTIME_SOURCE_ID:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_SOURCE_MISMATCH", "the runtime source is not the Reactor Product owner"
        )

    authority_generation = _current_authority_generation(runtime_client)
    status = _read_runtime_status(runtime_client, binding_id)
    installation_id = _validate_runtime_status(status, binding_id)
    installation = _read_installation(runtime_client, installation_id)
    package_version = _validate_installation(installation, installation_id)
    control_url = control_url_from_connection_ref(_required_string(status, "connection_ref"))

    try:
        engine = RemoteServingExecutionPort(
            ServingBindingConfiguration(
                binding_id=binding_id,
                control_url=control_url,
                credential_file=binding_configuration.credential_file,
            ),
            require_owner_protected_credential=True,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_CREDENTIAL_INVALID", "the owner credential file is unavailable"
        ) from exc

    try:
        metadata = engine.request("GET", "/metadata")
    except Exception as exc:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_METADATA_UNAVAILABLE",
            "the receipt endpoint could not provide metadata",
        ) from exc
    _validate_endpoint_metadata(metadata, package_version)

    latest_status = _read_runtime_status(runtime_client, binding_id)
    _validate_runtime_status(latest_status, binding_id)
    if (
        latest_status.get("installation_id") != installation_id
        or latest_status.get("generation") != status.get("generation")
        or latest_status.get("connection_ref") != status.get("connection_ref")
    ):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_RECEIPT_CHANGED", "the runtime changed during owner admission"
        )
    if _current_authority_generation(runtime_client) != authority_generation:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_AUTHORITY_CHANGED",
            "the current source authority changed during admission",
        )
    return engine


def _runtime_client_from_environment() -> PackageRuntimeClientProtocol:
    """Load only the pinned SDK read client when package mode is configured.

    中文:仅在启用包模式时加载已安装 SDK 的只读客户端。
    """

    try:
        sdk = import_module("cyrene_runtime_maintenance")
    except ImportError as exc:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_SDK_MISSING", "the PackageRuntime SDK is not installed"
        ) from exc
    client_type = getattr(sdk, "PackageRuntimeClient", None)
    if client_type is None or not callable(getattr(client_type, "from_environment", None)):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_SDK_INCOMPATIBLE",
            "the installed SDK has no read-only PackageRuntime client",
        )
    try:
        client = client_type.from_environment()
    except Exception as exc:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_SOURCE_UNAVAILABLE", "Reactor source credentials are unavailable"
        ) from exc
    return cast(PackageRuntimeClientProtocol, client)


def _current_authority_generation(client: PackageRuntimeClientProtocol) -> int:
    """Fetch a fresh authenticated source authority generation. | 获取当前授权代次。"""

    try:
        authority = client.authority()
    except Exception as exc:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_AUTHORITY_UNAVAILABLE", "the current source authority is unavailable"
        ) from exc
    if (
        not isinstance(authority, Mapping)
        or authority.get("authority") != "platform_package_runtime"
        or authority.get("protocol_version") != PACKAGE_RUNTIME_CONTROL_PROTOCOL
    ):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_AUTHORITY_INVALID", "the daemon authority protocol is incompatible"
        )
    generation = authority.get("catalog_generation")
    sdk_generation = getattr(client, "catalog_generation", None)
    capabilities = authority.get("capabilities")
    if (
        not isinstance(generation, int)
        or isinstance(generation, bool)
        or generation <= 0
        or sdk_generation != generation
        or not isinstance(capabilities, list)
        or not capabilities
        or not all(isinstance(item, str) for item in capabilities)
    ):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_AUTHORITY_INVALID", "the source authority snapshot is incomplete"
        )
    return generation


def _read_runtime_status(
    client: PackageRuntimeClientProtocol, binding_id: str
) -> Mapping[str, Any]:
    """Read one binding status through the SDK's source-authorized method.

    中文:通过 SDK 的 source 授权只读方法获取绑定状态。
    """

    try:
        result = client.runtime_status(binding_id)
    except Exception as exc:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_OWNER_READ_DENIED", "the source cannot read the configured binding"
        ) from exc
    if not isinstance(result, Mapping):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_RECEIPT_INVALID", "the runtime status response is invalid"
        )
    return result


def _read_installation(
    client: PackageRuntimeClientProtocol, installation_id: str
) -> Mapping[str, Any]:
    """Read the installation returned by RuntimeStatus without choosing an ID.

    中文:仅按 RuntimeStatus 返回的安装 ID 只读获取安装记录。
    """

    try:
        result = client.get_installation(installation_id)
    except Exception as exc:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_OWNER_READ_DENIED", "the source cannot read the runtime installation"
        ) from exc
    if not isinstance(result, Mapping):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_INSTALLATION_INVALID", "the installation record is invalid"
        )
    return result


def _validate_runtime_status(status: Mapping[str, Any], binding_id: str) -> str:
    """Require a live receipt for the exact configured PackageRuntime binding.

    中文:要求回执绑定 ID 完全匹配且运行状态来自真实 supervisor。
    """

    installation_id = _required_string(status, "installation_id")
    generation = status.get("generation")
    if (
        status.get("binding_id") != binding_id
        or status.get("state") != "RUNNING"
        or not _BINDING_ID.fullmatch(installation_id)
        or not isinstance(generation, int)
        or isinstance(generation, bool)
        or generation <= 0
    ):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_NOT_RUNNING", "the configured package binding is not running"
        )
    _required_string(status, "connection_ref")
    return installation_id


def _validate_installation(installation: Mapping[str, Any], installation_id: str) -> str:
    """Match receipt installation identity to verified package capability metadata.

    中文:核对安装回执、包身份、能力与验证摘要。
    """

    package_version = _required_string(installation, "package_version")
    capabilities = installation.get("capabilities")
    verification = installation.get("verification")
    record_version = installation.get("record_version")
    if (
        not isinstance(record_version, int)
        or isinstance(record_version, bool)
        or record_version != 1
        or installation.get("installation_id") != installation_id
        or installation.get("package_id") != PACKAGE_RUNTIME_PACKAGE_ID
        or not _PACKAGE_VERSION.fullmatch(package_version)
        or installation.get("state") != "INSTALLED"
        or not isinstance(capabilities, list)
        or not all(isinstance(capability, str) for capability in capabilities)
        or PACKAGE_RUNTIME_CAPABILITY_ID not in capabilities
        or not isinstance(verification, Mapping)
        or not _SHA256.fullmatch(str(verification.get("manifest_digest", "")))
        or not _SHA256.fullmatch(str(installation.get("artifact_digest", "")))
        or not _SHA256.fullmatch(str(installation.get("archive_digest", "")))
    ):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_INSTALLATION_MISMATCH",
            "the receipt does not reference a verified vLLM execution package",
        )
    return package_version


def _validate_endpoint_metadata(metadata: Mapping[str, Any], package_version: str) -> None:
    """Cross-check the Plugin endpoint against its verified installed package.

    中文:将插件端点元数据与已验证安装记录交叉核对。
    """

    expected = {
        "package_id": PACKAGE_RUNTIME_PACKAGE_ID,
        "package_version": package_version,
        "capability": PACKAGE_RUNTIME_CAPABILITY_ID,
        "interface_version": PACKAGE_RUNTIME_INTERFACE_VERSION,
        "transport": PACKAGE_RUNTIME_HTTP_TRANSPORT,
    }
    if not isinstance(metadata, Mapping) or dict(metadata) != expected:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_METADATA_MISMATCH",
            "the endpoint metadata does not match the verified package",
        )


def _required_string(document: Mapping[str, Any], field: str) -> str:
    """Return a non-empty, bounded identity string without control characters.

    中文:读取非空且长度受限、无控制字符的身份字符串。
    """

    value = document.get(field)
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 2048
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_RECEIPT_INVALID", f"the runtime response has invalid {field}"
        )
    return value
