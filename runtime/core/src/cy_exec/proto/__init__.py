"""Generated CY-LLM protobuf messages and gRPC bindings."""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/proto/__init__.py
# │ Module: runtime/core/src/cy_exec/proto/__init__
# │ Role: Canonical Reactor inference runtime — manages engines, scheduling, health, and serving protocols.
# │
# │ 模块职责：Reactor 标准推理运行时——管理引擎、调度、健康检查与服务协议。
# └─────────────────────────────────────────────────────────────────────┘


from . import ai_service_pb2, ai_service_pb2_grpc
from .ai_service_pb2 import (
    ControlMessage,
    GenerationParameters,
    StreamMetadata,
    StreamPredictRequest,
    StreamPredictResponse,
    WorkerHealthRequest,
    WorkerHealthResponse,
)
from .ai_service_pb2_grpc import (
    AiInferenceServicer,
    AiInferenceStub,
    add_AiInferenceServicer_to_server,
)

__all__ = [
    "ai_service_pb2",
    "ai_service_pb2_grpc",
    "ControlMessage",
    "GenerationParameters",
    "StreamMetadata",
    "StreamPredictRequest",
    "StreamPredictResponse",
    "WorkerHealthRequest",
    "WorkerHealthResponse",
    "AiInferenceServicer",
    "AiInferenceStub",
    "add_AiInferenceServicer_to_server",
]
