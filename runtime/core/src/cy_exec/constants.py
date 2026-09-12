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

    # 兼容旧名称
    MAX_MESSAGE_SIZE: Final[int] = MAX_MESSAGE_SIZE_BYTES

    # Keepalive 配置 (毫秒)
    KEEPALIVE_TIME_MS: Final[int] = 30_000
    KEEPALIVE_TIMEOUT_MS: Final[int] = 10_000
    MIN_PING_INTERVAL_MS: Final[int] = 10_000

    # 并发工作线程数
    DEFAULT_WORKERS: Final[int] = 10
    MAX_WORKERS: Final[int] = DEFAULT_WORKERS

    # 兼容旧名称
    TIMEOUT_SECONDS: Final[int] = 30

    # Prompt 长度限制（字符数）
    PROMPT_MAX_CHARS: Final[int] = 50_000


class MemoryDefaults:
    """显存管理相关常量"""
    # GPU 显存使用阈值
    GPU_MEMORY_THRESHOLD: Final[float] = 0.90
    GPU_THRESHOLD: Final[float] = GPU_MEMORY_THRESHOLD

    # 自动检查间隔 (秒)
    CHECK_INTERVAL_SECONDS: Final[int] = 60
    CLEANUP_INTERVAL: Final[int] = CHECK_INTERVAL_SECONDS

    # 锁清理触发阈值
    LOCK_CLEANUP_THRESHOLD: Final[int] = 100
    LOCK_CLEANUP_INTERVAL: Final[int] = LOCK_CLEANUP_THRESHOLD


class QueueDefaults:
    """队列相关常量"""
    # 默认队列大小
    DEFAULT_SIZE: Final[int] = 128


class UnitConversions:
    """单位换算常量"""
    # 字节转换
    BYTES_PER_KB: Final[int] = 1024
    BYTES_PER_MB: Final[int] = 1024 * 1024
    BYTES_PER_GB: Final[int] = 1024 * 1024 * 1024

    # 兼容旧测试
    KB: Final[int] = BYTES_PER_KB
    MB: Final[int] = BYTES_PER_MB
    GB: Final[int] = BYTES_PER_GB

    # 毫秒转换
    MS_PER_SECOND: Final[int] = 1000
    NS_PER_MS: Final[int] = 1_000_000


# 便捷访问
__all__ = [
    "GRPCDefaults",
    "MemoryDefaults",
    "QueueDefaults",
    "UnitConversions",
]
