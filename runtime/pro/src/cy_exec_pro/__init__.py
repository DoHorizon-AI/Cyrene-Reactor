"""Optional Pro extensions for the Reactor execution runtime."""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/pro/src/cy_exec_pro/__init__.py
# │ Module: runtime/pro/src/cy_exec_pro/__init__
# │ Role: Optional Reactor Product observability extensions.
# │
# │ 模块职责：提供可选的 Reactor Product 可观测性扩展。
# └─────────────────────────────────────────────────────────────────────┘


from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cy-exec-pro")
except PackageNotFoundError:
    __version__ = "0.1.0"


__all__ = ["__version__"]
