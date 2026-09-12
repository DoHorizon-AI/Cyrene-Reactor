"""Optional Pro extensions for the Reactor execution runtime."""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/pro/src/cy_exec_pro/__init__.py
# │ Module: runtime/pro/src/cy_exec_pro/__init__
# │ Role: Optional Reactor Pro runtime — adds relay, hardware, cache, LoRA, and coordination extensions.
# │
# │ 模块职责：Reactor 可选 Pro 运行时——提供中继、硬件、缓存、LoRA 与协调扩展。
# └─────────────────────────────────────────────────────────────────────┘


from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cy-exec-pro")
except PackageNotFoundError:
    __version__ = "0.1.0"


__all__ = ["__version__"]
