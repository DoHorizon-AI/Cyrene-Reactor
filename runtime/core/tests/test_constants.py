"""Tests for active Reactor runtime constants."""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/tests/test_constants.py
# │ Module: runtime/core/tests/test_constants
# │ Role: Verify active gRPC and bounded-queue defaults.
# │
# │ 模块职责：验证仍在使用的 gRPC 与有界队列默认值。
# └─────────────────────────────────────────────────────────────────────┘

from cy_exec import constants
from cy_exec.constants import GRPCDefaults, QueueDefaults


def test_grpc_defaults_are_valid() -> None:
    assert 1 <= GRPCDefaults.PORT <= 65535
    assert GRPCDefaults.MAX_MESSAGE_SIZE_BYTES == 100 * 1024 * 1024
    assert GRPCDefaults.DEFAULT_WORKERS > 0
    assert GRPCDefaults.KEEPALIVE_TIME_MS > GRPCDefaults.KEEPALIVE_TIMEOUT_MS


def test_queue_default_is_bounded() -> None:
    assert QueueDefaults.DEFAULT_SIZE > 0


def test_removed_hardware_and_compatibility_constants_do_not_return() -> None:
    assert not hasattr(constants, "MemoryDefaults")
    assert not hasattr(constants, "UnitConversions")
    assert not hasattr(GRPCDefaults, "MAX_MESSAGE_SIZE")
    assert not hasattr(GRPCDefaults, "MAX_WORKERS")
    assert not hasattr(GRPCDefaults, "TIMEOUT_SECONDS")
