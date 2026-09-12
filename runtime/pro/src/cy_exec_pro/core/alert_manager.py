"""Thread-safe threshold alerts with de-duplication and recovery events."""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/pro/src/cy_exec_pro/core/alert_manager.py
# │ Module: runtime/pro/src/cy_exec_pro/core/alert_manager
# │ Role: Optional Reactor Pro runtime — adds relay, hardware, cache, LoRA, and coordination extensions.
# │
# │ 模块职责：Reactor 可选 Pro 运行时——提供中继、硬件、缓存、LoRA 与协调扩展。
# └─────────────────────────────────────────────────────────────────────┘


from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

LOGGER = logging.getLogger("cy_exec_pro.core.alert_manager")


class AlertLevel(Enum):
    """Alert severity."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Supported monitored signals."""

    GPU_UTILIZATION = "gpu_utilization"
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
        gpu_utilization_threshold: float = 80.0,
        queue_depth_threshold: int = 100,
        memory_pressure_threshold: float = 90.0,
        latency_threshold_ms: float = 5000.0,
    ) -> None:
        self._lock = threading.Lock()
        self._gpu_threshold = gpu_utilization_threshold
        self._queue_threshold = queue_depth_threshold
        self._memory_threshold = memory_pressure_threshold
        self._latency_threshold = latency_threshold_ms
        self._alert_states: Dict[AlertType, bool] = {
            alert_type: False for alert_type in AlertType
        }
        self._alert_history: List[Alert] = []
        self._max_history = 1000
        self._callbacks: List[Callable[[Alert], None]] = []
        LOGGER.info(
            "AlertManager initialized: GPU=%f%%, Queue=%d, Memory=%f%%, Latency=%fms",
            gpu_utilization_threshold,
            queue_depth_threshold,
            memory_pressure_threshold,
            latency_threshold_ms,
        )

    def check_gpu_utilization(self, utilization: float) -> Optional[Alert]:
        """Check GPU utilization against its threshold."""
        return self._check(
            AlertType.GPU_UTILIZATION,
            utilization,
            self._gpu_threshold,
            AlertLevel.WARNING,
            lambda value, threshold: (
                f"GPU utilization too high: {value:.1f}% (threshold: {threshold}%)",
                f"GPU utilization recovered: {value:.1f}%",
            ),
        )

    def check_queue_depth(self, depth: int) -> Optional[Alert]:
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

    def check_memory_pressure(self, pressure: float) -> Optional[Alert]:
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

    def check_latency(self, latency_ms: float) -> Optional[Alert]:
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
    ) -> Optional[Alert]:
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

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
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


_alert_manager: Optional[AlertManager] = None


def get_alert_manager(
    gpu_threshold: float = 80.0,
    queue_threshold: int = 100,
    memory_threshold: float = 90.0,
    latency_threshold_ms: float = 5000.0,
) -> AlertManager:
    """Return the process-wide alert manager singleton."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(
            gpu_utilization_threshold=gpu_threshold,
            queue_depth_threshold=queue_threshold,
            memory_pressure_threshold=memory_threshold,
            latency_threshold_ms=latency_threshold_ms,
        )
    return _alert_manager


__all__ = ["Alert", "AlertLevel", "AlertManager", "AlertType", "get_alert_manager"]
