"""Property tests migrated from the Pro alert manager tests."""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/pro/tests/test_alert_manager_pbt.py
# │ Module: runtime/pro/tests/test_alert_manager_pbt
# │ Role: Optional Pro runtime test module — verifies enterprise serving extensions.
# │
# │ 模块职责：可选 Pro 运行时测试模块——验证企业级服务扩展。
# └─────────────────────────────────────────────────────────────────────┘


from hypothesis import given, settings, strategies as st

from cy_exec_pro.core.alert_manager import AlertLevel, AlertManager, AlertType


@given(values=st.lists(st.floats(0, 100, allow_nan=False, allow_infinity=False), min_size=1, max_size=20))
@settings(max_examples=30, deadline=None)
def test_gpu_alert_deduplication_and_state(values):
    manager = AlertManager(gpu_utilization_threshold=80.0)
    alerts = [alert for value in values if (alert := manager.check_gpu_utilization(value))]
    for first, second in zip(alerts, alerts[1:]):
        assert first.resolved != second.resolved
    assert manager.get_alert_state(AlertType.GPU_UTILIZATION) is (values[-1] > 80.0)


@given(values=st.lists(st.integers(0, 200), min_size=1, max_size=20))
@settings(max_examples=30, deadline=None)
def test_queue_alert_threshold(values):
    manager = AlertManager(queue_depth_threshold=100)
    for value in values:
        manager.check_queue_depth(value)
    assert manager.get_alert_state(AlertType.QUEUE_DEPTH) is (values[-1] > 100)


def test_memory_and_latency_levels_and_callbacks():
    manager = AlertManager(memory_pressure_threshold=90, latency_threshold_ms=5000)
    seen = []
    manager.register_callback(seen.append)
    memory_alert = manager.check_memory_pressure(95)
    latency_alert = manager.check_latency(6000)
    assert memory_alert is not None and memory_alert.level == AlertLevel.CRITICAL
    assert latency_alert is not None and latency_alert.level == AlertLevel.WARNING
    assert len(seen) == 2
    assert manager.check_memory_pressure(90).resolved
    manager.reset()
    assert manager.get_alert_history() == []
