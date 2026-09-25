"""Tests for Reactor's Product-owned model residency registry.

中文：Reactor Product 所有模型驻留注册表的测试。"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/tests/test_memory_manager.py
# │ Module: runtime/core/tests/test_memory_manager
# │ Role: Verify model identity and Plugin-reported memory observations.
# │
# │ 模块职责：验证模型驻留身份与插件上报的内存观测。
# └─────────────────────────────────────────────────────────────────────┘

from __future__ import annotations

import threading
from unittest.mock import Mock

from cy_exec.core.memory_manager import ModelResidencyRegistry


def test_registry_tracks_only_loaded_engine_handles() -> None:
    registry = ModelResidencyRegistry()
    engine = Mock()

    registry.register_model("model", engine)

    assert registry.get_loaded_model("model") is engine
    assert registry.get_loaded_models() == ["model"]

    registry.unregister_model("model")
    assert registry.get_loaded_model("model") is None
    assert registry.get_loaded_models() == []


def test_registry_instances_do_not_share_product_state() -> None:
    first = ModelResidencyRegistry()
    second = ModelResidencyRegistry()

    first.register_model("model", Mock())

    assert first.get_loaded_models() == ["model"]
    assert second.get_loaded_models() == []


def test_memory_observation_aggregates_plugin_reports() -> None:
    first_engine = Mock()
    first_engine.get_memory_usage.return_value = {"allocated_gb": 1.5, "total_gb": 8.0}
    second_engine = Mock()
    second_engine.get_memory_usage.return_value = {"allocated_gb": 2.0, "total_gb": 16.0}
    registry = ModelResidencyRegistry()
    registry.register_model("first", first_engine)
    registry.register_model("second", second_engine)

    assert registry.memory_observation() == {
        "available": True,
        "allocated_gb": 3.5,
        "total_gb": 24.0,
        "reporting_engines": 2.0,
    }


def test_invalid_plugin_observation_does_not_invent_hardware_facts() -> None:
    engine = Mock()
    engine.get_memory_usage.side_effect = ValueError("observation unavailable")
    registry = ModelResidencyRegistry()
    registry.register_model("model", engine)

    assert registry.memory_observation() == {
        "available": False,
        "allocated_gb": 0.0,
        "total_gb": 0.0,
        "reporting_engines": 0.0,
    }


def test_registration_is_thread_safe() -> None:
    registry = ModelResidencyRegistry()
    threads = [threading.Thread(target=registry.register_model, args=(f"model-{index}", Mock())) for index in range(20)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert set(registry.get_loaded_models()) == {f"model-{index}" for index in range(20)}


def test_removed_hardware_and_compatibility_apis_do_not_return() -> None:
    registry = ModelResidencyRegistry()
    forbidden = {
        "acquire_lock",
        "check_memory_and_evict",
        "force_cleanup",
        "get_eviction_candidates",
        "get_memory_info",
        "release_lock",
        "should_evict",
    }

    assert forbidden.isdisjoint(dir(registry))
