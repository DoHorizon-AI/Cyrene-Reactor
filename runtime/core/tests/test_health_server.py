"""Unit tests for the health server fail-closed semantics.

中文:健康服务器失败即拒绝语义的单元测试。"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/tests/test_health_server.py
# │ Module: runtime/core/tests/test_health_server
# │ Role: Core runtime test module — verifies the canonical inference worker behavior.
# │
# │ 模块职责：核心运行时测试模块——验证标准推理工作器的行为。
# └─────────────────────────────────────────────────────────────────────┘

import json
import threading
import urllib.request

import pytest
from cy_exec.core.telemetry import Telemetry
from cy_exec.health.health_server import start_health_server


def test_health_server_healthy_status() -> None:
    server = start_health_server(port=0, health_checker=lambda: True)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/healthz")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ok"
    finally:
        server.shutdown()
        server.server_close()


def test_health_server_unhealthy_status() -> None:
    server = start_health_server(port=0, health_checker=lambda: False)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/healthz")
        try:
            urllib.request.urlopen(req)
            pytest.fail("Expected HTTP 503 error")
        except urllib.error.HTTPError as err:
            assert err.code == 503
            data = json.loads(err.read().decode("utf-8"))
            assert data["status"] == "unhealthy"
    finally:
        server.shutdown()
        server.server_close()


def test_metrics_endpoint_exports_supplied_server_telemetry() -> None:
    telemetry = Telemetry()
    telemetry.track_request_start()
    telemetry.track_request_end(0.01, success=True)
    server = start_health_server(port=0, telemetry=telemetry)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics") as response:
            metrics = response.read().decode("utf-8")
        assert "reactor_requests_success_total 1" in metrics
        assert "gpu" not in metrics.lower()
        assert "cache" not in metrics.lower()
    finally:
        server.shutdown()
        server.server_close()
