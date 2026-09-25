"""Collect Product request telemetry without cache or hardware authority.

中文:收集 Product 请求遥测,不拥有缓存或硬件事实。"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/core/telemetry.py
# │ Module: runtime/core/src/cy_exec/core/telemetry
# │ Role: Reactor request, latency, error, and token telemetry.
# │
# │ 模块职责：收集 Reactor 请求、延迟、错误与 token 指标。
# └─────────────────────────────────────────────────────────────────────┘

from __future__ import annotations

import threading
from collections import deque


def _percentile(sorted_data: list[float], percentile: float) -> float:
    """Return a linearly interpolated percentile in seconds.

        中文:返回以秒为单位、通过线性插值计算的百分位数。"""
    if not sorted_data:
        return 0.0
    position = (len(sorted_data) - 1) * percentile / 100.0
    lower = int(position)
    upper = min(lower + 1, len(sorted_data) - 1)
    return sorted_data[lower] + (position - lower) * (sorted_data[upper] - sorted_data[lower])


class Telemetry:
    """Collect metrics for one Reactor server instance.

        中文:收集一个 Reactor 服务实例的指标。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests_inflight = 0
        self._requests_success = 0
        self._requests_failed = 0
        self._tokens_total = 0
        self._latencies: deque[float] = deque(maxlen=512)

    def track_request_start(self) -> None:
        """Record that one request entered execution.

            中文:记录一条请求已进入执行阶段。"""
        with self._lock:
            self._requests_inflight += 1

    def track_request_end(self, latency_seconds: float, *, success: bool) -> None:
        """Record the terminal outcome and latency of one request.

            中文:记录一条请求的最终结果和延迟。"""
        with self._lock:
            self._requests_inflight = max(0, self._requests_inflight - 1)
            if success:
                self._requests_success += 1
            else:
                self._requests_failed += 1
            self._latencies.append(latency_seconds)

    def track_token_generated(self, tokens: int) -> None:
        """Add generated output tokens to the Product counter.

            中文:将生成的输出 token 数累加到 Product 计数器。"""
        with self._lock:
            self._tokens_total += int(tokens)

    def snapshot(self) -> dict[str, float]:
        """Return the canonical metrics consumed by health adapters.

            中文:返回健康适配器使用的规范指标。"""
        with self._lock:
            sorted_latencies = sorted(self._latencies)
            average = sum(sorted_latencies) / len(sorted_latencies) if sorted_latencies else 0.0
            return {
                "requests_inflight": float(self._requests_inflight),
                "requests_success": float(self._requests_success),
                "requests_failed": float(self._requests_failed),
                "latency_avg_ms": average * 1000.0,
                "latency_p50_ms": _percentile(sorted_latencies, 50) * 1000.0,
                "latency_p95_ms": _percentile(sorted_latencies, 95) * 1000.0,
                "latency_p99_ms": _percentile(sorted_latencies, 99) * 1000.0,
                "tokens_total": float(self._tokens_total),
            }

    def reset(self) -> None:
        """Reset this server's metrics.

            中文:重置此服务器的指标。"""
        with self._lock:
            self._requests_inflight = 0
            self._requests_success = 0
            self._requests_failed = 0
            self._tokens_total = 0
            self._latencies.clear()

    def export_prometheus(self) -> str:
        """Serialize the canonical Product metrics in Prometheus text form.

            中文:将规范 Product 指标序列化为 Prometheus 文本格式。"""
        data = self.snapshot()
        lines = [
            "# HELP reactor_requests_inflight Current number of inflight requests",
            "# TYPE reactor_requests_inflight gauge",
            f"reactor_requests_inflight {data['requests_inflight']:.0f}",
            "# HELP reactor_requests_success_total Total successful requests",
            "# TYPE reactor_requests_success_total counter",
            f"reactor_requests_success_total {data['requests_success']:.0f}",
            "# HELP reactor_requests_failed_total Total failed requests",
            "# TYPE reactor_requests_failed_total counter",
            f"reactor_requests_failed_total {data['requests_failed']:.0f}",
            "# HELP reactor_request_latency_ms Request latency in milliseconds",
            "# TYPE reactor_request_latency_ms summary",
            f'reactor_request_latency_ms{{quantile="0.5"}} {data["latency_p50_ms"]:.2f}',
            f'reactor_request_latency_ms{{quantile="0.95"}} {data["latency_p95_ms"]:.2f}',
            f'reactor_request_latency_ms{{quantile="0.99"}} {data["latency_p99_ms"]:.2f}',
            f"reactor_request_latency_ms_avg {data['latency_avg_ms']:.2f}",
            "# HELP reactor_tokens_total Total generated tokens",
            "# TYPE reactor_tokens_total counter",
            f"reactor_tokens_total {data['tokens_total']:.0f}",
        ]
        return "\n".join(lines)
