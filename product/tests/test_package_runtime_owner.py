"""Owner-scoped PackageRuntime receipt admission tests. | 包运行回执准入测试。"""

from __future__ import annotations

import json
import threading
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

import cyrene_reactor_product.cli as reactor_cli
from cyrene_reactor_product.package_runtime_owner import (
    PACKAGE_RUNTIME_CAPABILITY_ID,
    PACKAGE_RUNTIME_PACKAGE_ID,
    PackageRuntimeBindingFailure,
    control_url_from_connection_ref,
    package_runtime_engine,
)
from cyrene_reactor_product.remote_engine import RemoteServingExecutionPort

_TOKEN = "package-runtime-owner-test-token-000000000000"
_DIGEST = "sha256:" + "a" * 64


class _PackageRuntimeClientStub:
    """Read-only SDK fixture that records which calls admission makes.

    中文:仅模拟 SDK 的只读 source 方法,用于验证 Reactor 不执行生命周期操作。
    """

    source_id = "cyrene-reactor"
    catalog_generation = 7

    def __init__(self, connection_ref: str) -> None:
        self.connection_ref = connection_ref
        self.status: dict[str, Any] = {
            "binding_id": "reactor.vllm-import.primary",
            "installation_id": "install-actual-001",
            "generation": 3,
            "state": "RUNNING",
            "connection_ref": connection_ref,
        }
        self.installation: dict[str, Any] = {
            "record_version": 1,
            "installation_id": "install-actual-001",
            "package_id": PACKAGE_RUNTIME_PACKAGE_ID,
            "package_version": "0.1.0",
            "artifact_digest": _DIGEST,
            "archive_digest": _DIGEST,
            "capabilities": [PACKAGE_RUNTIME_CAPABILITY_ID],
            "state": "INSTALLED",
            "verification": {"manifest_digest": _DIGEST},
        }
        self.authority_generations = [7, 7]
        self.calls: list[tuple[str, str | None]] = []

    def authority(self) -> Mapping[str, Any]:
        self.calls.append(("authority", None))
        generation = self.authority_generations.pop(0)
        self.catalog_generation = generation
        return {
            "authority": "platform_package_runtime",
            "protocol_version": "cy-package-runtime.control.v1",
            "catalog_generation": generation,
            "capabilities": ["package_runtime_binding_operation"],
        }

    def runtime_status(self, binding_id: str) -> Mapping[str, Any]:
        self.calls.append(("runtime_status", binding_id))
        return dict(self.status)

    def get_installation(self, installation_id: str) -> Mapping[str, Any]:
        self.calls.append(("get_installation", installation_id))
        return dict(self.installation)


@pytest.fixture
def metadata_server() -> tuple[int, list[str]]:
    """Serve a bearer-protected metadata response on actual IPv4 loopback.

    中文:在真实动态分配的 IPv4 环回端口上提供仅元数据的测试端点。
    """

    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            if self.headers.get("Authorization") != f"Bearer {_TOKEN}":
                self.send_error(403)
                return
            if self.path != "/metadata":
                self.send_error(404)
                return
            body = {
                "package_id": PACKAGE_RUNTIME_PACKAGE_ID,
                "package_version": "0.1.0",
                "capability": PACKAGE_RUNTIME_CAPABILITY_ID,
                "interface_version": "1",
                "transport": "http",
            }
            encoded = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], requests
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def _credential_file(path: Path, *, mode: int = 0o600) -> Path:
    path.write_text(_TOKEN, encoding="utf-8")
    path.chmod(mode)
    return path


def test_receipt_resolves_to_authenticated_live_loopback_metadata(
    tmp_path: Path, metadata_server: tuple[int, list[str]]
) -> None:
    """Admit only a running, source-owned package receipt and metadata endpoint.

    中文:仅接受 source 授权的运行回执及其认证元数据。
    """

    port, requests = metadata_server
    connection_ref = f"cyrene-http-v1://127.0.0.1:{port}"
    client = _PackageRuntimeClientStub(connection_ref)
    credential = _credential_file(tmp_path / "serving.token")

    engine = package_runtime_engine(
        "reactor.vllm-import.primary",
        {"credential_file": credential},
        client=client,
    )

    assert engine.binding.binding_id == "reactor.vllm-import.primary"
    assert engine.binding.control_url == f"http://127.0.0.1:{port}"
    assert requests == ["/metadata"]
    assert client.calls == [
        ("authority", None),
        ("runtime_status", "reactor.vllm-import.primary"),
        ("get_installation", "install-actual-001"),
        ("runtime_status", "reactor.vllm-import.primary"),
        ("authority", None),
    ]


@pytest.mark.parametrize(
    "connection_ref",
    [
        "https://127.0.0.1:41000",
        "cyrene-http-v1://localhost:41000",
        "cyrene-http-v1://127.0.0.2:41000",
        "cyrene-http-v1://[::1]:41000",
        "cyrene-http-v1://0.0.0.0:41000",
        "cyrene-http-v1://user@127.0.0.1:41000",
        "cyrene-http-v1://127.0.0.1:41000/path",
        "cyrene-http-v1://127.0.0.1:41000?token=x",
        "cyrene-http-v1://127.0.0.1:41000#fragment",
        "cyrene-http-v1://127.0.0.1:0",
        "cyrene-http-v1://127.0.0.1:65536",
        "cyrene-http-v1://127.0.0.1:041000",
    ],
)
def test_connection_ref_rejects_untyped_or_non_loopback_addresses(connection_ref: str) -> None:
    """Reject caller-style URLs and every non-canonical connection reference.

    中文:拒绝用户 URL 及非规范连接引用。
    """

    with pytest.raises(PackageRuntimeBindingFailure) as error:
        control_url_from_connection_ref(connection_ref)

    assert error.value.code == "PACKAGE_RUNTIME_CONNECTION_REF_INVALID"


def test_connection_ref_accepts_only_canonical_actual_port() -> None:
    assert (
        control_url_from_connection_ref("cyrene-http-v1://127.0.0.1:41000")
        == "http://127.0.0.1:41000"
    )


def test_owner_configuration_rejects_caller_control_url() -> None:
    """Accept only an owner credential path, never a configured raw URL.

    中文:绑定配置只允许 owner 凭证路径,不接受可注入的原始 URL。
    """

    with pytest.raises(PackageRuntimeBindingFailure) as error:
        package_runtime_engine(
            "reactor.vllm-import.primary",
            {
                "credential_file": "/run/secrets/serving.token",
                "control_url": "https://caller.example",
            },
            client=_PackageRuntimeClientStub("cyrene-http-v1://127.0.0.1:41000"),
        )

    assert error.value.code == "PACKAGE_RUNTIME_CONFIGURATION_INVALID"


@pytest.mark.parametrize(
    ("change", "expected_code"),
    [
        ("source", "PACKAGE_RUNTIME_SOURCE_MISMATCH"),
        ("stopped", "PACKAGE_RUNTIME_NOT_RUNNING"),
        ("wrong_binding", "PACKAGE_RUNTIME_NOT_RUNNING"),
        ("invalid_installation_id", "PACKAGE_RUNTIME_NOT_RUNNING"),
        ("wrong_installation", "PACKAGE_RUNTIME_INSTALLATION_MISMATCH"),
        ("wrong_package", "PACKAGE_RUNTIME_INSTALLATION_MISMATCH"),
        ("wrong_record_version", "PACKAGE_RUNTIME_INSTALLATION_MISMATCH"),
        ("invalid_package_version", "PACKAGE_RUNTIME_INSTALLATION_MISMATCH"),
        ("missing_capability", "PACKAGE_RUNTIME_INSTALLATION_MISMATCH"),
        ("invalid_digest", "PACKAGE_RUNTIME_INSTALLATION_MISMATCH"),
        ("authority_changed", "PACKAGE_RUNTIME_AUTHORITY_CHANGED"),
        ("non_http_ref", "PACKAGE_RUNTIME_CONNECTION_REF_INVALID"),
    ],
)
def test_owner_admission_fails_closed_on_inconsistent_evidence(
    tmp_path: Path,
    metadata_server: tuple[int, list[str]],
    change: str,
    expected_code: str,
) -> None:
    """Reject stale authority, wrong identity and non-running receipt evidence.

    中文:对授权代次、包身份及运行状态不一致的证据全部 fail closed。
    """

    port, requests = metadata_server
    connection_ref = f"cyrene-http-v1://127.0.0.1:{port}"
    client = _PackageRuntimeClientStub(connection_ref)
    if change == "source":
        client.source_id = "other-product"
    elif change == "stopped":
        client.status["state"] = "STOPPED"
    elif change == "wrong_binding":
        client.status["binding_id"] = "other-binding"
    elif change == "invalid_installation_id":
        client.status["installation_id"] = "i"
    elif change == "wrong_installation":
        client.installation["installation_id"] = "different-installation"
    elif change == "wrong_package":
        client.installation["package_id"] = "other.package"
    elif change == "wrong_record_version":
        client.installation["record_version"] = 2
    elif change == "invalid_package_version":
        client.installation["package_version"] = "0.1.0/evil"
    elif change == "missing_capability":
        client.installation["capabilities"] = ["memory.provider.v1"]
    elif change == "invalid_digest":
        client.installation["verification"]["manifest_digest"] = "sha256:invalid"
    elif change == "authority_changed":
        client.authority_generations = [7, 8]
    elif change == "non_http_ref":
        client.status["connection_ref"] = "https://remote.example/control"
    credential = _credential_file(tmp_path / "serving.token")

    with pytest.raises(PackageRuntimeBindingFailure) as error:
        package_runtime_engine(
            "reactor.vllm-import.primary",
            {"credential_file": credential},
            client=client,
        )

    assert error.value.code == expected_code
    if expected_code != "PACKAGE_RUNTIME_AUTHORITY_CHANGED":
        assert requests == []


@pytest.mark.parametrize("credential_mode", [0o640, 0o604, 0o700, 0o000])
def test_package_binding_rejects_group_or_world_readable_credentials(
    tmp_path: Path,
    metadata_server: tuple[int, list[str]],
    credential_mode: int,
) -> None:
    """Require a readable owner-private credential file before endpoint access.

    中文:连接插件端点前只接受 owner 私有的可读凭证文件。
    """

    port, requests = metadata_server
    client = _PackageRuntimeClientStub(f"cyrene-http-v1://127.0.0.1:{port}")
    credential = _credential_file(tmp_path / "serving.token", mode=credential_mode)

    with pytest.raises(PackageRuntimeBindingFailure) as error:
        package_runtime_engine(
            "reactor.vllm-import.primary",
            {"credential_file": credential},
            client=client,
        )

    assert error.value.code == "PACKAGE_RUNTIME_CREDENTIAL_INVALID"
    assert requests == []


def test_package_binding_rejects_symlinked_credentials(
    tmp_path: Path,
    metadata_server: tuple[int, list[str]],
) -> None:
    """Never follow a credential symlink even when the target is private.

    中文:即使目标文件权限安全,也拒绝凭证符号链接。
    """

    port, requests = metadata_server
    client = _PackageRuntimeClientStub(f"cyrene-http-v1://127.0.0.1:{port}")
    credential = _credential_file(tmp_path / "serving.token")
    link = tmp_path / "serving-link.token"
    link.symlink_to(credential)

    with pytest.raises(PackageRuntimeBindingFailure) as error:
        package_runtime_engine(
            "reactor.vllm-import.primary",
            {"credential_file": link},
            client=client,
        )

    assert error.value.code == "PACKAGE_RUNTIME_CREDENTIAL_INVALID"
    assert requests == []


def test_owner_admission_rejects_endpoint_metadata_not_matching_installation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require endpoint identity and interface data to match the installed record.

    中文:插件端点元数据必须与已安装记录的包版本和接口身份一致。
    """

    client = _PackageRuntimeClientStub("cyrene-http-v1://127.0.0.1:41000")
    credential = _credential_file(tmp_path / "serving.token")
    requests: list[tuple[str, str]] = []

    def mismatching_metadata(
        engine: RemoteServingExecutionPort,
        method: str,
        path: str,
        payload: object = None,
    ) -> dict[str, Any]:
        del engine, payload
        requests.append((method, path))
        return {
            "package_id": PACKAGE_RUNTIME_PACKAGE_ID,
            "package_version": "0.1.0",
            "capability": PACKAGE_RUNTIME_CAPABILITY_ID,
            "interface_version": "2",
            "transport": "http",
        }

    monkeypatch.setattr(RemoteServingExecutionPort, "request", mismatching_metadata)
    with pytest.raises(PackageRuntimeBindingFailure) as error:
        package_runtime_engine(
            "reactor.vllm-import.primary",
            {"credential_file": credential},
            client=client,
        )

    assert error.value.code == "PACKAGE_RUNTIME_METADATA_MISMATCH"
    assert requests == [("GET", "/metadata")]


def test_legacy_explicit_binding_remains_available_without_package_sdk(
    tmp_path: Path,
) -> None:
    """Keep the prior explicit static binding path when package mode is absent.

    中文:未配置包运行时 owner 模式时继续支持原有显式静态绑定。
    """

    credential = _credential_file(tmp_path / "serving.token")
    engines = reactor_cli._engines(
        {
            "serving_bindings": [
                {
                    "binding_id": "legacy",
                    "control_url": "https://node.example",
                    "credential_file": credential,
                }
            ]
        }
    )

    assert set(engines) == {"legacy"}
    assert engines["legacy"].binding.control_url == "https://node.example"  # type: ignore[attr-defined]


def test_configured_package_mode_never_returns_static_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail startup when configured owner admission fails despite a static URL.

    中文:包 owner 准入失败时即使存在静态 URL 也不返回回退引擎。
    """

    credential = _credential_file(tmp_path / "serving.token")
    static_credential = _credential_file(tmp_path / "static.token")

    def reject_package_binding(_binding_id: str, _configuration: Mapping[str, Any]) -> None:
        raise PackageRuntimeBindingFailure(
            "PACKAGE_RUNTIME_SDK_MISSING", "the PackageRuntime SDK is not installed"
        )

    monkeypatch.setattr(reactor_cli, "package_runtime_engine", reject_package_binding)
    with pytest.raises(PackageRuntimeBindingFailure) as error:
        reactor_cli._engines(
            {
                "serving_bindings": [
                    {
                        "binding_id": "legacy-static",
                        "control_url": "https://static.example",
                        "credential_file": static_credential,
                    }
                ],
                "package_runtime_bindings": {
                    "reactor.vllm-import.primary": {"credential_file": credential}
                },
            }
        )

    assert error.value.code == "PACKAGE_RUNTIME_SDK_MISSING"
