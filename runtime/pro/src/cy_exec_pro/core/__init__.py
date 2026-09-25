"""Pro-only runtime coordination helpers.

Submodules are intentionally not imported here so importing the package does
not probe optional GPU/NPU libraries or start a service.

中文：仅供 Pro 使用的运行时协调辅助项。

中文：此处有意不导入子模块，避免导入软件包时探测可选 GPU/NPU 库或启动服务。
"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/pro/src/cy_exec_pro/core/__init__.py
# │ Module: runtime/pro/src/cy_exec_pro/core/__init__
# │ Role: Optional Product-side alert and coordination helpers.
# │
# │ 模块职责：提供可选的 Product 告警与协调辅助能力。
# └─────────────────────────────────────────────────────────────────────┘


__all__: list[str] = []
