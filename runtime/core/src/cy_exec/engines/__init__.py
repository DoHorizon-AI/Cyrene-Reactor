"""Product-owned execution-engine port types.

Concrete inference engines live in ``Cyrene-Plugins-Official`` and are reached
through the versioned direct Plugin runtime.
"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/engines/__init__.py
# │ Module: runtime/core/src/cy_exec/engines/__init__
# │ Role: Canonical Reactor inference runtime — manages engines, scheduling, health, and serving protocols.
# │
# │ 模块职责：Reactor 标准推理运行时——管理引擎、调度、健康检查与服务协议。
# └─────────────────────────────────────────────────────────────────────┘


from .abstract_engine import BaseEngine

__all__ = ["BaseEngine"]
