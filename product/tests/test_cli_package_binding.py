"""Package Runtime CLI request construction and safety tests. | 测试包运行时 CLI 请求。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import cyrene_reactor_product.cli as reactor_cli

_BINDING_ID = "reactor.vllm-import.primary"
_REQUEST_ID = "f4e4db4e-0752-47ef-9c31-63d03fe157d1"
_TOKEN = "reactor-control-test-token-with-enough-entropy"


class _Response:
    """Minimal HTTP response fixture for package-binding CLI requests."""

    is_success = True

    @staticmethod
    def json() -> dict[str, Any]:
        return {
            "bindingId": _BINDING_ID,
            "requestId": _REQUEST_ID,
            "phase": "COMPLETED",
            "operation_token": "private-operation-token-never-print",
        }


def _credential(path: Path) -> Path:
    path.write_text(_TOKEN, encoding="utf-8")
    path.chmod(0o600)
    return path


def test_activate_requires_installation_id_before_sending_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing installation identity keeps the explicit CLI error and sends nothing."""

    monkeypatch.setenv("REACTOR_PACKAGE_RUNTIME_BINDING_ID", _BINDING_ID)
    monkeypatch.setattr(
        reactor_cli.httpx,
        "request",
        lambda *_args, **_kwargs: pytest.fail(
            "request must not be sent without an installation ID"
        ),
    )

    with pytest.raises(SystemExit, match="PACKAGE_RUNTIME_INSTALLATION_ID_REQUIRED"):
        reactor_cli._package_binding(
            {"credential_file": _credential(tmp_path / "control.token")},
            "activate",
            _REQUEST_ID,
        )


@pytest.mark.parametrize(
    ("command", "installation_id", "method", "suffix", "body"),
    [
        (
            "activate",
            "install-actual-001",
            "POST",
            "/actions/activate",
            {"installationId": "install-actual-001"},
        ),
        ("deactivate", None, "POST", "/actions/deactivate", None),
        ("reconcile", None, "POST", "/actions/reconcile", None),
        ("status", None, "GET", "", None),
    ],
)
def test_package_binding_commands_keep_request_method_and_body(
    command: str,
    installation_id: str | None,
    method: str,
    suffix: str,
    body: dict[str, str] | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Forward each lifecycle command with its established method and payload."""

    monkeypatch.setenv("REACTOR_PACKAGE_RUNTIME_BINDING_ID", _BINDING_ID)
    calls: list[tuple[str, str, dict[str, str], Any, float]] = []

    def request(
        actual_method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: Any,
        timeout: float,
    ) -> _Response:
        calls.append((actual_method, url, headers, json, timeout))
        return _Response()

    monkeypatch.setattr(reactor_cli.httpx, "request", request)

    result = reactor_cli._package_binding(
        {
            "credential_file": _credential(tmp_path / f"{command}.token"),
            "control_url": "http://127.0.0.1:19300/",
        },
        command,
        _REQUEST_ID,
        installation_id,
    )

    assert result == 0
    assert len(calls) == 1
    actual_method, url, headers, actual_body, timeout = calls[0]
    assert actual_method == method
    assert url == f"http://127.0.0.1:19300/api/v1/runtime-bindings/{_BINDING_ID}{suffix}"
    assert actual_body == body
    assert headers["Authorization"] == f"Bearer {_TOKEN}"
    if command == "status":
        assert "Idempotency-Key" not in headers
    else:
        assert headers["Idempotency-Key"] == _REQUEST_ID
    assert timeout == 30.0
    output = capsys.readouterr().out
    assert _TOKEN not in output
    assert "private-operation-token-never-print" not in output
