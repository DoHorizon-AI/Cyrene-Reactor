"""
utils - Worker 工具模块

包含：
  - auth: 认证工具
  - path_utils: 路径安全工具
  - stream_buffer: 流式缓冲
Concrete model loading, compatibility checks, and hardware tuning are
Plugins/Platform-owned.
"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/utils/__init__.py
# │ Module: runtime/core/src/cy_exec/utils/__init__
# │ Role: Canonical Reactor inference runtime — manages engines, scheduling, health, and serving protocols.
# │
# │ 模块职责：Reactor 标准推理运行时——管理引擎、调度、健康检查与服务协议。
# └─────────────────────────────────────────────────────────────────────┘


from .auth import (
    verify_token,
    verify_grpc_context,
    verify_grpc_context_async,
)
from .path_utils import (
    PathTraversalError,
    safe_join,
    validate_model_path,
    is_safe_filename,
    sanitize_filename,
)

__all__ = [
    # auth
    # 中文:认证
    "verify_token",
    "verify_grpc_context",
    "verify_grpc_context_async",
    # path_utils
    # 中文:路径工具
    "PathTraversalError",
    "safe_join",
    "validate_model_path",
    "is_safe_filename",
    "sanitize_filename",
]
