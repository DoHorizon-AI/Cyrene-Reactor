# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/health/health_server.py
# │ Module: runtime/core/src/cy_exec/health/health_server
# │ Role: Canonical Reactor inference runtime — manages engines, scheduling, health, and serving protocols.
# │
# │ 模块职责：Reactor 标准推理运行时——管理引擎、调度、健康检查与服务协议。
# └─────────────────────────────────────────────────────────────────────┘

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional

try:
    from cy_exec.core.telemetry import Telemetry
except ImportError:
    Telemetry = None


class HealthHTTPServer(HTTPServer):
    allow_reuse_address = True

    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        health_checker: Optional[Callable[[], bool]] = None,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.health_checker = health_checker


class _HealthHandler(BaseHTTPRequestHandler):
    telemetry = Telemetry() if Telemetry is not None else None

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/healthz", "/metrics"):
            self.send_response(404)
            self.end_headers()
            return

        if self.path == "/healthz":
            checker = getattr(self.server, "health_checker", None)
            is_healthy = True
            if checker is not None:
                try:
                    is_healthy = bool(checker())
                except Exception:
                    is_healthy = False

            if is_healthy:
                payload = {"status": "ok"}
                self.send_response(200)
            else:
                payload = {"status": "unhealthy"}
                self.send_response(503)

            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=True).encode("utf-8"))
            return

        metrics = self.telemetry.export_prometheus() if self.telemetry else ""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(metrics.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


# ════════════════════════════════════════════════════════════════════════
# 🔧 FUNCTION: start_health_server
#
#   Creates the HTTP health/metrics server used to expose readiness and
#   Prometheus-compatible telemetry at the serving boundary.
#
#   创建服务边界使用的健康/指标 HTTP 服务，暴露就绪状态与 Prometheus 兼容遥测。
#
# ════════════════════════════════════════════════════════════════════════
def start_health_server(
    port: Optional[int] = None,
    health_checker: Optional[Callable[[], bool]] = None,
) -> HealthHTTPServer:
    target_port = 0 if port == 0 else (port or int(os.getenv("CY_LLM_HEALTH_PORT", "9090")))
    server = HealthHTTPServer(("0.0.0.0", target_port), _HealthHandler, health_checker=health_checker)
    return server
