"""Thread-safe threshold alerts with de-duplication and recovery events."""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/pro/src/cy_exec_pro/core/alert_manager.py
# │ Module: runtime/pro/src/cy_exec_pro/core/alert_manager
# │ Role: Optional Product alerts for queue, pressure, and latency signals.
# │
# │ 模块职责：为队列、资源压力与请求延迟提供可选 Product 告警。
# └─────────────────────────────────────────────────────────────────────┘

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

LOGGER = logging.getLogger("cy_exec_pro.core.alert_manager")


class AlertLevel(Enum):
    """Alert severity."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Supported monitored signals."""

    QUEUE_DEPTH = "queue_depth"
    MEMORY_PRESSURE = "memory_pressure"
    LATENCY_HIGH = "latency_high"


@dataclass
class Alert:
    """One alert or recovery event."""

    alert_type: AlertType
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: float
    resolved: bool = False


class AlertManager:
    """Emit one alert per threshold excursion until recovery."""

    def __init__(
        self,
        queue_depth_threshold: int = 100,
        memory_pressure_threshold: float = 90.0,
        latency_threshold_ms: float = 5000.0,
    ) -> None:
        self._lock = threading.Lock()
        self._queue_threshold = queue_depth_threshold
        self._memory_threshold = memory_pressure_threshold
        self._latency_threshold = latency_threshold_ms
        self._alert_states: dict[AlertType, bool] = {alert_type: False for alert_type in AlertType}
        self._alert_history: list[Alert] = []
        self._max_history = 1000
        self._callbacks: list[Callable[[Alert], None]] = []
        LOGGER.info(
            "AlertManager initialized: Queue=%d, Memory=%f%%, Latency=%fms",
            queue_depth_threshold,
            memory_pressure_threshold,
            latency_threshold_ms,
        )

    def check_queue_depth(self, depth: int) -> Alert | None:
        """Check queue depth against its threshold."""
        return self._check(
            AlertType.QUEUE_DEPTH,
            float(depth),
            float(self._queue_threshold),
            AlertLevel.WARNING,
            lambda value, threshold: (
                f"Queue depth too high: {int(value)} (threshold: {int(threshold)})",
                f"Queue depth recovered: {int(value)}",
            ),
        )

    def check_memory_pressure(self, pressure: float) -> Alert | None:
        """Check memory pressure against its threshold."""
        return self._check(
            AlertType.MEMORY_PRESSURE,
            pressure,
            self._memory_threshold,
            AlertLevel.CRITICAL,
            lambda value, threshold: (
                f"Memory pressure too high: {value:.1f}% (threshold: {threshold}%)",
                f"Memory pressure recovered: {value:.1f}%",
            ),
        )

    def check_latency(self, latency_ms: float) -> Alert | None:
        """Check latency against its threshold."""
        return self._check(
            AlertType.LATENCY_HIGH,
            latency_ms,
            self._latency_threshold,
            AlertLevel.WARNING,
            lambda value, threshold: (
                f"Latency too high: {value:.1f}ms (threshold: {threshold}ms)",
                f"Latency recovered: {value:.1f}ms",
            ),
        )

    def _check(
        self,
        alert_type: AlertType,
        value: float,
        threshold: float,
        level: AlertLevel,
        messages: Callable[[float, float], tuple[str, str]],
    ) -> Alert | None:
        """Apply common threshold, recovery, and callback behavior."""
        with self._lock:
            if value > threshold:
                if self._alert_states[alert_type]:
                    return None
                message, _ = messages(value, threshold)
                alert = Alert(
                    alert_type=alert_type,
                    level=level,
                    message=message,
                    value=value,
                    threshold=threshold,
                    timestamp=time.time(),
                )
                self._alert_states[alert_type] = True
            else:
                if not self._alert_states[alert_type]:
                    return None
                _, message = messages(value, threshold)
                alert = Alert(
                    alert_type=alert_type,
                    level=AlertLevel.INFO,
                    message=message,
                    value=value,
                    threshold=threshold,
                    timestamp=time.time(),
                    resolved=True,
                )
                self._alert_states[alert_type] = False

            self._record_alert(alert)
            self._trigger_callbacks(alert)
            return alert

    def register_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register an alert callback."""
        with self._lock:
            self._callbacks.append(callback)

    def get_alert_state(self, alert_type: AlertType) -> bool:
        """Return whether an alert type is currently active."""
        with self._lock:
            return self._alert_states.get(alert_type, False)

    def get_alert_history(self, limit: int = 100) -> list[Alert]:
        """Return up to ``limit`` recent alert events."""
        with self._lock:
            return self._alert_history[-limit:]

    def _record_alert(self, alert: Alert) -> None:
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history :]

    def _trigger_callbacks(self, alert: Alert) -> None:
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as exc:
                LOGGER.error("Alert callback failed: %s", exc)

    def reset(self) -> None:
        """Clear active states and alert history."""
        with self._lock:
            for alert_type in self._alert_states:
                self._alert_states[alert_type] = False
            self._alert_history.clear()


__all__ = ["Alert", "AlertLevel", "AlertManager", "AlertType"]
