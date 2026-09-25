"""Tests for canonical Reactor request telemetry.

中文：Reactor 规范请求遥测的测试。"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/tests/test_telemetry.py
# │ Module: runtime/core/tests/test_telemetry
# │ Role: Verify request metrics without cache or hardware authority.
# │
# │ 模块职责：验证不包含缓存或硬件权威的请求指标。
# └─────────────────────────────────────────────────────────────────────┘

from __future__ import annotations

import threading

from cy_exec.core.telemetry import Telemetry


def test_request_lifecycle_uses_canonical_health_fields() -> None:
    telemetry = Telemetry()
    telemetry.track_request_start()
    telemetry.track_request_end(0.125, success=True)
    telemetry.track_token_generated(3)

    snapshot = telemetry.snapshot()

    assert snapshot["requests_inflight"] == 0.0
    assert snapshot["requests_success"] == 1.0
    assert snapshot["requests_failed"] == 0.0
    assert snapshot["latency_p50_ms"] == 125.0
    assert snapshot["tokens_total"] == 3.0


def test_failed_request_is_counted_once() -> None:
    telemetry = Telemetry()
    telemetry.track_request_start()
    telemetry.track_request_end(0.01, success=False)

    snapshot = telemetry.snapshot()
    assert snapshot["requests_failed"] == 1.0
    assert snapshot["requests_success"] == 0.0


def test_instances_do_not_share_product_metrics() -> None:
    first = Telemetry()
    second = Telemetry()
    first.track_request_start()

    assert first.snapshot()["requests_inflight"] == 1.0
    assert second.snapshot()["requests_inflight"] == 0.0


def test_thread_safe_request_tracking() -> None:
    telemetry = Telemetry()

    def complete_request() -> None:
        telemetry.track_request_start()
        telemetry.track_request_end(0.001, success=True)

    threads = [threading.Thread(target=complete_request) for _ in range(100)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    snapshot = telemetry.snapshot()
    assert snapshot["requests_inflight"] == 0.0
    assert snapshot["requests_success"] == 100.0


def test_reset_clears_all_metrics() -> None:
    telemetry = Telemetry()
    telemetry.track_request_start()
    telemetry.track_request_end(0.1, success=True)
    telemetry.track_token_generated(5)

    telemetry.reset()

    assert set(telemetry.snapshot().values()) == {0.0}


def test_prometheus_export_contains_only_product_metrics() -> None:
    telemetry = Telemetry()
    telemetry.track_request_start()
    telemetry.track_request_end(0.05, success=True)

    output = telemetry.export_prometheus()

    assert "reactor_requests_success_total 1" in output
    assert "reactor_request_latency_ms" in output
    assert "cache" not in output.lower()
    assert "gpu" not in output.lower()
