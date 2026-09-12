"""
grpc_servicer.py
[gRPC 服务实现] 实现 AiInferenceServicer，桥接 gRPC 接口与 InferenceServer
"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/grpc_servicer.py
# │ Module: runtime/core/src/cy_exec/grpc_servicer
# │ Role: Canonical Reactor inference runtime — manages engines, scheduling, health, and serving protocols.
# │
# │ 模块职责：Reactor 标准推理运行时——管理引擎、调度、健康检查与服务协议。
# └─────────────────────────────────────────────────────────────────────┘


from __future__ import annotations

import logging
import time
import uuid
from concurrent import futures
from typing import Generator, Iterator, Optional

import grpc
try:
	from opentelemetry import trace  # type: ignore
	from opentelemetry.trace.status import Status, StatusCode  # type: ignore
except ImportError:
	trace = None
	Status = None
	StatusCode = None

from cy_exec.proto import (
    AiInferenceServicer,
    ControlMessage,
    StreamPredictRequest,
    StreamPredictResponse,
    WorkerHealthRequest,
    WorkerHealthResponse,
    add_AiInferenceServicer_to_server,
)
from .config.config_loader import WorkerConfig, load_worker_config
from .core.server import InferenceServer
from .core.telemetry import Telemetry
from .constants import GRPCDefaults
from .exceptions import (
    EWWorkerError,
    EngineError,
    ModelError,
    ResourceError,
    GPUMemoryError,
)
from .utils.auth import verify_grpc_context
from .utils.tls import GRPCTLSConfig, load_grpc_tls_config

LOGGER = logging.getLogger("cy_llm.worker.grpc")


def _verify_internal_token(context: grpc.ServicerContext) -> bool:
    """验证来自 Gateway 的内部 Token"""
    return verify_grpc_context(context)


# ════════════════════════════════════════════════════════════════════════
# 🔧 CLASS: AiInferenceServicerImpl
#
#   Bridges the generated gRPC service contract to InferenceServer while
#   preserving streaming, authentication, cancellation, and health semantics.
#
#   将生成的 gRPC 服务契约桥接到 InferenceServer，并保持流式、认证、取消与健康语义。
#
# ════════════════════════════════════════════════════════════════════════
class AiInferenceServicerImpl(AiInferenceServicer):
    """AiInference gRPC 服务实现"""

    def __init__(
        self,
        inference_server: InferenceServer,
        config: Optional[WorkerConfig] = None,
        telemetry: Optional[Telemetry] = None,
    ) -> None:
        self._server = inference_server
        self._config = config or load_worker_config()
        self._telemetry = telemetry or Telemetry()

    def StreamPredict(
        self,
        request_iterator: Iterator[StreamPredictRequest],
        context: grpc.ServicerContext,
    ) -> Generator[StreamPredictResponse, None, None]:
        """双向流推理接口"""
        if not _verify_internal_token(context):
            return

        # 从第一个请求获取推理参数
        try:
            first_request = next(request_iterator)
        except StopIteration:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Empty request stream")
            return

        trace_id = first_request.metadata.trace_id if first_request.metadata else str(uuid.uuid4())
        model_id = first_request.model_id or "default"
        prompt = first_request.prompt
        if len(prompt) > GRPCDefaults.PROMPT_MAX_CHARS:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Prompt too long (max {GRPCDefaults.PROMPT_MAX_CHARS} chars)",
            )
            return
        adapter = first_request.adapter or None
        priority = first_request.priority or 0

        # 解析生成参数
        gen_params = first_request.generation
        generation_kwargs = {}
        if gen_params:
            if gen_params.max_new_tokens > 0:
                generation_kwargs["max_new_tokens"] = gen_params.max_new_tokens
            if gen_params.temperature > 0:
                generation_kwargs["temperature"] = gen_params.temperature
            if gen_params.top_p > 0:
                generation_kwargs["top_p"] = gen_params.top_p
            if gen_params.repetition_penalty > 0:
                generation_kwargs["repetition_penalty"] = gen_params.repetition_penalty

        span = None
        if trace is not None:
            tracer = trace.get_tracer("cy_llm.worker.grpc")
            span = tracer.start_span("worker.stream_predict")
            span.set_attribute("trace_id", trace_id)
            span.set_attribute("model_id", model_id)
            span.set_attribute("priority", priority)
        LOGGER.info(
            "[%s] StreamPredict 请求: model=%s prompt_len=%d priority=%d",
            trace_id, model_id, len(prompt), priority,
        )

        # 从模型注册表获取模型配置
        spec = self._config.model_registry.get(model_id)
        if spec is None:
            LOGGER.error("[%s] 模型 %s 未在注册表中找到", trace_id, model_id)
            context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Model '{model_id}' not found in registry",
            )
            return

        model_path = spec.model_path
        adapter_path = adapter or spec.adapter_path
        provider_id = spec.provider_id or self._config.provider_id
        engine_kwargs = {}

        # Pass owner-defined configuration through without interpreting vendor semantics.
        if spec.quantization:
            engine_kwargs["quantization"] = spec.quantization

        # KV Cache 配置
        if spec.max_model_len is not None:
            engine_kwargs["max_model_len"] = spec.max_model_len
        if spec.tensor_parallel_size is not None:
            engine_kwargs["tensor_parallel_size"] = spec.tensor_parallel_size
        if spec.enable_prefix_caching is not None:
            engine_kwargs["enable_prefix_caching"] = spec.enable_prefix_caching
        if spec.kv_cache_dtype is not None:
            engine_kwargs["kv_cache_dtype"] = spec.kv_cache_dtype
        if spec.gpu_memory_utilization is not None:
            engine_kwargs["gpu_memory_utilization"] = spec.gpu_memory_utilization

        start_time = time.perf_counter()
        first_token_time = None

        try:
            try:
                chunk_index = 0
                for chunk in self._server.stream_predict(
                    model_id=model_id,
                    prompt=prompt,
                    model_path=model_path,
                    adapter_path=adapter_path,
                    provider_id=provider_id,
                    generation_kwargs=generation_kwargs or None,
                    engine_kwargs=engine_kwargs or None,
                    priority=priority,
                ):
                    if chunk_index == 0:
                        first_token_time = time.perf_counter()

                    yield StreamPredictResponse(
                        trace_id=trace_id,
                        chunk=str(chunk),
                        end_of_stream=False,
                        index=chunk_index,
                    )
                    chunk_index += 1

                # 发送结束标记
                # 统计计算
                end_time = time.perf_counter()
                ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else 0

                # 计算生成速度 (TPS)
                gen_duration = end_time - first_token_time if first_token_time else (end_time - start_time)
                gen_duration = max(gen_duration, 0.001)

                # Chunks are transport units; report their observed rate without
                # interpreting a specific Plugin provider's tokenization.
                tokens_count = chunk_index
                tps = tokens_count / gen_duration

                yield StreamPredictResponse(
                    trace_id=trace_id,
                    chunk="",
                    end_of_stream=True,
                    index=chunk_index,
                    ttft_ms=ttft_ms,
                    tokens_per_sec=tps,
                )

                LOGGER.info(
                    "[%s] StreamPredict 完成: chunks=%d, speed=%.2f tok/s, ttft=%.2fms",
                    trace_id, chunk_index, tps, ttft_ms
                )
            except Exception as exc:
                if span is not None and Status is not None and StatusCode is not None:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
            finally:
                if span is not None:
                    span.end()

        except GPUMemoryError as exc:
            LOGGER.error("[%s] GPU 显存不足: %s", trace_id, exc)
            context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, str(exc))
        except ResourceError as exc:
            LOGGER.error("[%s] 资源错误: %s", trace_id, exc)
            context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, str(exc))
        except ModelError as exc:
            LOGGER.error("[%s] 模型错误: %s", trace_id, exc)
            context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
        except EngineError as exc:
            LOGGER.error("[%s] 引擎错误: %s", trace_id, exc)
            context.abort(grpc.StatusCode.INTERNAL, str(exc))
        except EWWorkerError as exc:
            LOGGER.error("[%s] Worker 错误: %s", trace_id, exc)
            context.abort(grpc.StatusCode.INTERNAL, str(exc))
        except RuntimeError as exc:
            LOGGER.error("[%s] 运行时错误: %s", trace_id, exc)
            context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, str(exc))
        except Exception as exc:
            LOGGER.exception("[%s] 未预期异常: %s", trace_id, exc)
            context.abort(grpc.StatusCode.INTERNAL, f"Internal error: {type(exc).__name__}")

    def Control(
        self,
        request: ControlMessage,
        context: grpc.ServicerContext,
    ) -> ControlMessage:
        """控制指令接口"""
        if not _verify_internal_token(context):
            return ControlMessage()

        trace_id = request.trace_id or str(uuid.uuid4())
        command = request.command
        payload = dict(request.payload)

        LOGGER.info("[%s] Control 指令: cmd=%s", trace_id, command)

        response_payload = {}

        if command == "unload_model":
            model_id = payload.get("model_id", "")
            if model_id:
                self._server.unload_model(model_id)
                response_payload["status"] = "ok"
                response_payload["message"] = f"Model {model_id} unloaded"
            else:
                response_payload["status"] = "error"
                response_payload["message"] = "Missing model_id"

        elif command == "list_models":
            models = list(self._config.model_registry.keys())
            response_payload["status"] = "ok"
            response_payload["models"] = ",".join(models)

        elif command == "ping":
            response_payload["status"] = "ok"
            response_payload["message"] = "pong"

        else:
            response_payload["status"] = "error"
            response_payload["message"] = f"Unknown command: {command}"

        return ControlMessage(
            trace_id=trace_id,
            command=f"{command}_response",
            payload=response_payload,
        )

    def Health(
        self,
        request: WorkerHealthRequest,
        context: grpc.ServicerContext,
    ) -> WorkerHealthResponse:
        """健康检查接口"""
        trace_id = request.trace_id or str(uuid.uuid4())

        # 收集指标
        metrics = {}
        try:
            snapshot = self._telemetry.snapshot()
            metrics["requests_inflight"] = str(snapshot.get("requests_inflight", 0))
            metrics["requests_success"] = str(snapshot.get("requests_success", 0))
            metrics["requests_failed"] = str(snapshot.get("requests_failed", 0))
            metrics["provider_id"] = self._config.provider_id
        except Exception as exc:
            LOGGER.warning("[%s] 获取指标失败: %s", trace_id, exc)

        return WorkerHealthResponse(
            healthy=True,
            metrics=metrics,
        )


def create_grpc_server(
    inference_server: InferenceServer,
    config: WorkerConfig,
    uds_path: str = "/tmp/cy_worker.sock",
    port: Optional[int] = None,
    max_workers: int = GRPCDefaults.DEFAULT_WORKERS,
    telemetry: Optional[Telemetry] = None,
) -> grpc.Server:
    """创建并配置 gRPC 服务器（支持 UDS & TCP）

    Args:
        inference_server: 推理服务器实例
        config: Worker 配置
        uds_path: Unix Domain Socket 路径 (仅支持 Linux/WSL)
        port: TCP 端口 (可选)
        max_workers: 线程池大小
        telemetry: 遥测实例

    Raises:
        RuntimeError: 如果不在 Linux/WSL 环境下运行
    """
    import platform
    import os

    # 强制检查 Linux 环境
    if platform.system() != "Linux":
        raise RuntimeError(
            f"CY-LLM Worker 仅支持 Linux/WSL 环境 (当前: {platform.system()})。"
            "UDS 通信需要 Linux 内核支持。"
        )

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            ("grpc.max_send_message_length", GRPCDefaults.MAX_MESSAGE_SIZE_BYTES),
            ("grpc.max_receive_message_length", GRPCDefaults.MAX_MESSAGE_SIZE_BYTES),
            ("grpc.keepalive_time_ms", GRPCDefaults.KEEPALIVE_TIME_MS),
            ("grpc.keepalive_timeout_ms", GRPCDefaults.KEEPALIVE_TIMEOUT_MS),
            ("grpc.keepalive_permit_without_calls", True),
        ],
    )

    # 注册推理服务
    inference_servicer = AiInferenceServicerImpl(
        inference_server=inference_server,
        config=config,
        telemetry=telemetry,
    )
    add_AiInferenceServicer_to_server(inference_servicer, server)
    LOGGER.info("已注册推理服务 (AiInference)")

    # 清理旧的 socket 文件
    if os.path.exists(uds_path):
        os.unlink(uds_path)
        LOGGER.info("已清理旧的 UDS 文件: %s", uds_path)

    # 启用 UDS (Unix Domain Socket)
    server.add_insecure_port(f"unix://{uds_path}")
    LOGGER.info("gRPC 已启用 UDS 通信: %s", uds_path)

    # 启用 TCP (如果指定)
    if port:
        server.add_insecure_port(f"[::]:{port}")
        LOGGER.info("gRPC 已启用 TCP 监听: 0.0.0.0:%d", port)
    else:
        LOGGER.warning("未指定 TCP 端口，仅通过 UDS 提供服务")

    return server
