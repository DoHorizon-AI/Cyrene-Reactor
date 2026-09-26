"""Verify the optional tracing dependency failure stays observable.

中文:验证可选追踪依赖缺失时仍有可观测日志。"""

from __future__ import annotations

import sys

import pytest

from cy_exec.utils.otel import init_tracing


def test_missing_otel_sdk_is_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A configured endpoint must produce a warning when its SDK is absent."""
    monkeypatch.setenv("CY_LLM_OTEL_ENDPOINT", "http://127.0.0.1:4317")
    monkeypatch.setitem(sys.modules, "opentelemetry", None)

    with caplog.at_level("WARNING", logger="cy_llm.worker.otel"):
        init_tracing("cyrene-reactor")

    assert "OpenTelemetry is unavailable" in caplog.text
    assert "ModuleNotFoundError" in caplog.text
