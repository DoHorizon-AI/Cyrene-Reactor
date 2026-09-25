"""Track Reactor-owned model residency over Plugins-owned engine handles.

中文：通过 Plugins 所有的引擎句柄跟踪 Reactor 所有的模型驻留状态。"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/core/memory_manager.py
# │ Module: runtime/core/src/cy_exec/core/memory_manager
# │ Role: Product model-residency registry over Plugin engine handles.
# │
# │ 模块职责：管理 Product 模型驻留记录与插件上报的内存观测。
# └─────────────────────────────────────────────────────────────────────┘

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engines.abstract_engine import BaseEngine


class ModelResidencyRegistry:
    """Own loaded-model identity without probing or releasing device memory.

        中文：持有已加载模型标识，但不探测或释放设备内存。"""

    def __init__(self) -> None:
        self._engines: dict[str, BaseEngine] = {}
        self._lock = threading.RLock()

    def register_model(self, model_id: str, engine: BaseEngine) -> None:
        """Record a successfully loaded Plugin engine handle.

            中文：记录一个已成功加载的 Plugin 引擎句柄。"""
        with self._lock:
            self._engines[model_id] = engine

    def unregister_model(self, model_id: str) -> None:
        """Remove a model after its Plugin confirms unload.

            中文：在 Plugin 确认卸载后移除模型。"""
        with self._lock:
            self._engines.pop(model_id, None)

    def get_loaded_model(self, model_id: str) -> BaseEngine | None:
        """Return the loaded Plugin engine for ``model_id`` when present.

            中文：若存在，则返回 ``model_id`` 对应的已加载 Plugin 引擎。"""
        with self._lock:
            return self._engines.get(model_id)

    def get_loaded_models(self) -> list[str]:
        """Return the model identities currently owned by this server.

            中文：返回当前由此服务器持有的模型标识。"""
        with self._lock:
            return list(self._engines)

    def memory_observation(self) -> dict[str, float | bool]:
        """Aggregate optional memory observations reported by loaded Plugins.

            中文：汇总已加载 Plugin 可选上报的内存观测。"""
        with self._lock:
            engines = tuple(self._engines.values())

        allocated_gb = 0.0
        total_gb = 0.0
        reporting_engines = 0
        for engine in engines:
            try:
                observation = engine.get_memory_usage()
                allocated_gb += float(observation.get("allocated_gb", 0.0))
                total_gb += float(observation.get("total_gb", 0.0))
                reporting_engines += 1
            except (AttributeError, TypeError, ValueError):
                continue

        return {
            "available": reporting_engines > 0,
            "allocated_gb": allocated_gb,
            "total_gb": total_gb,
            "reporting_engines": float(reporting_engines),
        }
