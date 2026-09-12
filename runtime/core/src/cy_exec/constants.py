"""
constants.py
统一管理 Worker 模块中的常量和默认值

使用方式：
    from cy_exec.constants import GRPCDefaults
"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/constants.py
# │ Module: runtime/core/src/cy_exec/constants
# │ Role: Canonical Reactor inference runtime — manages engines, scheduling, health, and serving protocols.
# │
# │ 模块职责：Reactor 标准推理运行时——管理引擎、调度、健康检查与服务协议。
# └─────────────────────────────────────────────────────────────────────┘


from typing import Final


class GRPCDefaults:
    """gRPC 服务相关常量"""
    # 默认端口
    PORT: Final[int] = 50051

    # 消息大小限制 (100MB)
    MAX_MESSAGE_SIZE_BYTES: Final[int] = 100 * 1024 * 1024

    # Keepalive 配置 (毫秒)
    KEEPALIVE_TIME_MS: Final[int] = 30_000
    KEEPALIVE_TIMEOUT_MS: Final[int] = 10_000
    MIN_PING_INTERVAL_MS: Final[int] = 10_000

    # 并发工作线程数
    DEFAULT_WORKERS: Final[int] = 10

    # Prompt 长度限制（字符数）
    PROMPT_MAX_CHARS: Final[int] = 50_000


class QueueDefaults:
    """队列相关常量"""
    # 默认队列大小
    DEFAULT_SIZE: Final[int] = 128


# 便捷访问
__all__ = [
    "GRPCDefaults",
    "QueueDefaults",
]
