"""Product-to-Plugin seam for the execution-engine capability.

中文：Product 到 Plugin 的执行引擎能力接口。"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Generator, Mapping
from dataclasses import dataclass
from enum import Enum
from threading import Event
from typing import Any, Protocol

from cyrene_plugin_runtime import (
    DirectPayload,
    DirectPluginClient,
    DirectPluginDeadlineExceeded,
    DirectPluginError,
    DirectPluginFailure,
    DirectPluginInvocationCancelled,
    DirectPluginProtocolError,
    DirectPluginTransportError,
)

from .engines.abstract_engine import BaseEngine

LOGGER = logging.getLogger("cy_llm.capability_seam")

EXECUTION_ENGINE_CAPABILITY = "execution.engine.v1"
EXECUTION_ENGINE_INTERFACE_VERSION = "1"
EXECUTION_ENGINE_TYPE_URL_PREFIX = "type.cyrene.io/execution.engine.v1"


def _execution_engine_type_url(method: str, direction: str) -> str:
    """Build the Plugins-owned JSON capability type URL. | 构造插件所有的类型 URL。"""

    return f"{EXECUTION_ENGINE_TYPE_URL_PREFIX}.{method}.{direction}"


class ServingProfile(str, Enum):
    """Operating profile for serving engine capability binding.

        中文：服务引擎能力绑定的运行配置。"""

    DIRECT_PLUGIN = "DIRECT_PLUGIN"


class ServingPortFailure(RuntimeError):
    """Stable Product failure raised when serving port binding fails or engine is unavailable.

        中文：服务端口绑定失败或引擎不可用时抛出的稳定 Product 错误。"""

    def __init__(self, message: str, *, status: int = 503, retryable: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable


@dataclass(frozen=True)
class ExecutionEngineRequirement:
    capability: str = EXECUTION_ENGINE_CAPABILITY
    interface_version: str = EXECUTION_ENGINE_INTERFACE_VERSION
    execution_modes: tuple[str, ...] = ("SERVICE", "WORKER")


EXECUTION_ENGINE_REQUIREMENT = ExecutionEngineRequirement()


@dataclass(frozen=True)
class ExecutionEngineBinding:
    """Binding configuration for serving engine capability.

        中文：服务引擎能力的绑定配置。"""

    profile: ServingProfile = ServingProfile.DIRECT_PLUGIN
    capability: str = EXECUTION_ENGINE_CAPABILITY
    connection_ref: str | None = None
    provider_id: str | None = None
    timeout_seconds: float = 30.0


class ExecutionEnginePort(Protocol):
    """Product serving port defining the contract consumed by Reactor.

        中文：定义 Reactor 所消费契约的 Product 服务端口。"""

    def load_model(self, model_path: str, **kwargs: Any) -> None: ...

    def infer(self, prompt: str, **kwargs: Any) -> Generator[str, None, None]: ...

    def unload_model(self) -> None: ...

    def get_model_info(self) -> dict[str, Any]: ...


class ExecutionEngineProvider(Protocol):
    def create(self, provider_id: str) -> BaseEngine: ...


class ExecutionEnginePluginResolver(Protocol):
    """Resolve one Plugins-owned engine contract without proxying through Platform.

        中文：解析一个由 Plugins 所有的引擎契约，不经 Platform 代理。"""

    def resolve(self, requirement: ExecutionEngineRequirement) -> ExecutionEngineProvider: ...


class DirectPluginExecutionEngineAdapter(BaseEngine):
    """Adapt Reactor's engine lifecycle to the Plugins-owned direct runtime.

    The capability payload remains JSON because ``execution.engine.v1`` owns a
    JSON Schema contract, but transport is always the versioned gRPC
    ``DirectPluginRuntime``.  Reactor never falls back to an in-tree engine
    after a direct invocation fails.

    将 Reactor 引擎生命周期适配到 Plugins 所有的直连运行时。载荷仍遵循
    ``execution.engine.v1`` 的 JSON Schema，但传输固定使用版本化 gRPC
    ``DirectPluginRuntime``；直连失败时绝不静默回退到本地引擎。
    """

    def __init__(self, binding: ExecutionEngineBinding, client: Any | None = None) -> None:
        self.binding = binding
        self._client = client
        self._is_loaded = False
        self._model_path: str | None = None
        self._engine_info: dict[str, Any] = {
            "engine": binding.provider_id or "direct-plugin-engine",
            "capability": binding.capability,
            "connection_ref": binding.connection_ref,
            "is_loaded": False,
        }

    def _get_client(self) -> Any:
        """Return the injected or SDK-created direct client. | 返回直连客户端。"""

        if self._client is not None:
            return self._client
        connection_ref = self.binding.connection_ref
        if not connection_ref:
            raise ServingPortFailure(
                "SERVING_BINDING_REQUIRED: direct plugin connection_ref is not configured",
                status=503,
            )
        try:
            self._client = DirectPluginClient.for_local_connection_ref(connection_ref)
        except (TypeError, ValueError) as exc:
            raise ServingPortFailure(
                f"SERVING_BINDING_INVALID: direct plugin connection_ref is invalid: {exc}",
                status=503,
            ) from exc
        return self._client

    @staticmethod
    def _json_bytes(payload: Mapping[str, Any]) -> bytes:
        """Encode one owner-defined JSON payload deterministically. | 编码 JSON 载荷。"""

        try:
            return json.dumps(
                dict(payload),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ServingPortFailure(
                f"DIRECT_PLUGIN_REQUEST_INVALID: payload is not JSON encodable: {exc}",
                status=500,
            ) from exc

    @staticmethod
    def _status_name(status: Any) -> str:
        return str(getattr(status, "name", status)).upper()

    @classmethod
    def _translate_direct_error(cls, error: DirectPluginError) -> ServingPortFailure:
        """Map SDK failures to the stable Reactor port error. | 映射稳定端口错误。"""

        if isinstance(error, DirectPluginInvocationCancelled) or (
            isinstance(error, DirectPluginFailure) and error.is_cancelled
        ):
            return ServingPortFailure(
                "DIRECT_PLUGIN_CANCELLED: direct Plugin invocation was cancelled",
                status=499,
            )

        if isinstance(error, DirectPluginDeadlineExceeded) or (
            isinstance(error, DirectPluginFailure) and error.code == 4
        ):
            return ServingPortFailure(
                f"DIRECT_PLUGIN_DEADLINE_EXCEEDED: {error}",
                status=504,
                retryable=True,
            )

        if isinstance(error, DirectPluginProtocolError):
            return ServingPortFailure(
                f"DIRECT_PLUGIN_PROTOCOL_ERROR: {error}",
                status=502,
            )

        if isinstance(error, DirectPluginFailure):
            code_names = {
                1: "INVALID_REQUEST",
                2: "METHOD_NOT_FOUND",
                3: "CANCELLED",
                4: "DEADLINE_EXCEEDED",
                5: "EXECUTION_FAILED",
                6: "UNAVAILABLE",
            }
            code_name = code_names.get(error.code, "UNKNOWN_FAILURE")
            status = 503 if error.code == 6 else 502
            return ServingPortFailure(
                f"DIRECT_PLUGIN_FAILURE[{error.domain_code or code_name}]: {error.message}",
                status=status,
                retryable=error.retryable or error.code == 6,
            )

        if isinstance(error, DirectPluginTransportError):
            status_name = cls._status_name(error.status)
            status = {
                "CANCELLED": 499,
                "DEADLINE_EXCEEDED": 504,
                "UNAVAILABLE": 503,
            }.get(status_name, 503)
            return ServingPortFailure(
                f"DIRECT_PLUGIN_TRANSPORT_ERROR[{status_name}]: {error.message}",
                status=status,
                retryable=status in {503, 504},
            )

        return ServingPortFailure(
            f"DIRECT_PLUGIN_ERROR: {error}",
            status=503,
            retryable=True,
        )

    def _invoke(
        self,
        method: str,
        payload: Mapping[str, Any],
        *,
        deadline_seconds: float | None = None,
        cancel_event: Event | None = None,
    ) -> dict[str, Any]:
        """Invoke one canonical method and validate its typed JSON response.

        The response type URL is checked before decoding so a corrupted or
        cross-capability payload cannot enter Product state.

            中文：调用一个规范方法并验证其有类型的 JSON 响应。

                中文：解码前会先检查响应类型 URL，防止损坏或跨能力载荷进入 Product 状态。
        """

        request_type_url = _execution_engine_type_url(method, "request")
        response_type_url = _execution_engine_type_url(method, "response")
        request = DirectPayload(request_type_url, self._json_bytes(payload))
        client = self._get_client()
        if cancel_event is not None and cancel_event.is_set():
            raise ServingPortFailure(
                "DIRECT_PLUGIN_CANCELLED: direct Plugin invocation was cancelled",
                status=499,
            )
        try:
            response = client.invoke(
                capability=EXECUTION_ENGINE_CAPABILITY,
                interface_version=EXECUTION_ENGINE_INTERFACE_VERSION,
                method=method,
                request=request,
                deadline_seconds=(self.binding.timeout_seconds if deadline_seconds is None else deadline_seconds),
                cancel_event=cancel_event,
            )
        except DirectPluginError as exc:
            raise self._translate_direct_error(exc) from exc
        except (TypeError, ValueError) as exc:
            raise ServingPortFailure(
                f"DIRECT_PLUGIN_PROTOCOL_ERROR: SDK invocation rejected the request: {exc}",
                status=502,
            ) from exc
        except Exception as exc:
            raise ServingPortFailure(
                f"DIRECT_PLUGIN_ERROR: direct Plugin invocation failed: {exc}",
                status=503,
                retryable=True,
            ) from exc

        if not isinstance(response, DirectPayload):
            raise ServingPortFailure(
                "DIRECT_PLUGIN_PROTOCOL_ERROR: response is not a typed DirectPayload",
                status=502,
            )
        if response.type_url != response_type_url:
            raise ServingPortFailure(
                "DIRECT_PLUGIN_PROTOCOL_ERROR: unexpected response type URL "
                f"{response.type_url!r}; expected {response_type_url!r}",
                status=502,
            )
        try:
            decoded = json.loads(response.value.decode("utf-8"))
        except (AttributeError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ServingPortFailure(
                f"DIRECT_PLUGIN_PROTOCOL_ERROR: response payload is not valid JSON: {exc}",
                status=502,
            ) from exc
        if not isinstance(decoded, dict):
            raise ServingPortFailure(
                "DIRECT_PLUGIN_PROTOCOL_ERROR: response payload must be a JSON object",
                status=502,
            )
        return decoded

    def load_model(
        self,
        model_path: str,
        adapter_path: str | None = None,
        **kwargs: Any,
    ) -> None:
        payload = {
            "model_path": model_path,
            "max_batch_size": kwargs.get("max_batch_size", 8),
        }
        if adapter_path:
            payload["adapter_path"] = adapter_path
        for field in (
            "adapter_name",
            "max_lora_rank",
            "max_model_len",
            "max_output_len",
            "quantization",
            "tensor_parallel_size",
            "gpu_memory_utilization",
            "enable_prefix_caching",
            "kv_cache_dtype",
        ):
            if kwargs.get(field) is not None:
                payload[field] = kwargs[field]
        resp = self._invoke(
            "load_model",
            payload,
            deadline_seconds=kwargs.get("deadline_seconds"),
        )
        if resp.get("status") != "LOADED" or not isinstance(resp.get("model_path"), str):
            raise ServingPortFailure(
                f"Model load rejected by direct plugin: {resp.get('detail', 'LOAD_FAILED')}",
                status=502,
            )
        self._is_loaded = True
        self._model_path = model_path
        self._engine_info["is_loaded"] = True
        self._engine_info["model_path"] = model_path

    def infer(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        if not self._is_loaded:
            raise ServingPortFailure("Model is not loaded. Call load_model() first.")

        cancel_event = kwargs.get("cancel_event")
        if kwargs.get("cancel_requested", False):
            cancel_event = Event()
            cancel_event.set()
        if cancel_event is not None and not hasattr(cancel_event, "is_set"):
            raise ServingPortFailure(
                "DIRECT_PLUGIN_REQUEST_INVALID: cancel_event must expose is_set()",
                status=500,
            )

        payload = {
            "prompt": prompt,
            "max_new_tokens": kwargs.get("max_tokens", kwargs.get("max_new_tokens", 512)),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
        }
        resp = self._invoke(
            "execute_inference",
            payload,
            deadline_seconds=kwargs.get("deadline_seconds"),
            cancel_event=cancel_event,
        )
        output_text = resp.get("output_text")
        if not isinstance(output_text, str) or not isinstance(resp.get("engine"), str):
            raise ServingPortFailure(
                "DIRECT_PLUGIN_PROTOCOL_ERROR: inference response is malformed",
                status=502,
            )
        yield output_text

    def unload_model(self) -> None:
        if not self._is_loaded:
            return
        try:
            resp = self._invoke("unload_model", {})
            if resp.get("status") != "UNLOADED" or not isinstance(resp.get("engine"), str):
                raise ServingPortFailure(
                    "DIRECT_PLUGIN_PROTOCOL_ERROR: unload response is malformed",
                    status=502,
                )
        except ServingPortFailure:
            # Keep state loaded when the remote endpoint did not confirm unload.
            # 远端未确认卸载时保留 loaded 状态，避免谎报生命周期事实。
            raise
        self._is_loaded = False
        self._model_path = None
        self._engine_info["is_loaded"] = False

    def get_memory_usage(self) -> dict[str, float]:
        return {
            "allocated_gb": 0.0,
            "reserved_gb": 0.0,
            "total_gb": 0.0,
            "utilization": 0.0,
        }

    def get_model_info(self) -> dict[str, Any]:
        if not self._is_loaded:
            return dict(self._engine_info)
        info = self._invoke("get_engine_info", {})
        required = ("engine_name", "runtime_available", "is_loaded")
        if any(key not in info for key in required):
            raise ServingPortFailure(
                "DIRECT_PLUGIN_PROTOCOL_ERROR: engine info response is malformed",
                status=502,
            )
        self._engine_info.update(info)
        return dict(self._engine_info)

    def health_check(self) -> bool:
        return self._is_loaded


class DirectPluginEngineProvider:
    """Provider returning DirectPluginExecutionEngineAdapter instances.

        中文：返回 DirectPluginExecutionEngineAdapter 实例的提供方。"""

    def __init__(self, binding: ExecutionEngineBinding, client: Any | None = None) -> None:
        self.binding = binding
        self._client = client

    def create(self, provider_id: str) -> BaseEngine:
        if provider_id != self.binding.provider_id:
            raise ServingPortFailure(
                "SERVING_PROVIDER_MISMATCH: requested provider does not match the bound Plugin",
                status=409,
            )
        if self._client is None:
            connection_ref = self.binding.connection_ref
            if not connection_ref:
                raise ServingPortFailure(
                    "SERVING_BINDING_REQUIRED: direct plugin connection_ref is not configured",
                    status=503,
                )
            try:
                self._client = DirectPluginClient.for_local_connection_ref(connection_ref)
            except (TypeError, ValueError) as exc:
                raise ServingPortFailure(
                    f"SERVING_BINDING_INVALID: direct plugin connection_ref is invalid: {exc}",
                    status=503,
                ) from exc
        return DirectPluginExecutionEngineAdapter(self.binding, client=self._client)


class ConfiguredExecutionEngineResolver:
    """Resolve the Plugins-owned execution engine with fail-closed semantics.

        中文：以失败即拒绝语义解析由 Plugins 所有的执行引擎。"""

    def __init__(
        self,
        binding: ExecutionEngineBinding,
        direct_client: Any | None = None,
    ) -> None:
        self._binding = binding
        self._direct_client = direct_client

    def resolve(self, requirement: ExecutionEngineRequirement) -> ExecutionEngineProvider:
        if requirement != EXECUTION_ENGINE_REQUIREMENT:
            raise ValueError(f"Unsupported serving capability requirement: {requirement}")

        if self._binding.profile == ServingProfile.DIRECT_PLUGIN:
            if not self._binding.connection_ref:
                raise ServingPortFailure(
                    "SERVING_BINDING_REQUIRED: direct plugin profile requires connection_ref",
                    status=503,
                )
            if not self._binding.provider_id:
                raise ServingPortFailure(
                    "SERVING_BINDING_REQUIRED: direct plugin profile requires provider_id",
                    status=503,
                )
            return DirectPluginEngineProvider(self._binding, client=self._direct_client)

        raise ServingPortFailure(
            f"SERVING_PROFILE_UNSUPPORTED: profile {self._binding.profile!r} is not supported",
            status=500,
        )


class ExecutionEngineCapabilityFactory:
    """Create a Product adapter for the explicitly bound Plugin provider.

        中文：为明确绑定的 Plugin 提供方创建 Product 适配器。"""

    def __init__(self, resolver: ExecutionEnginePluginResolver) -> None:
        self._resolver = resolver

    def __call__(self, provider_id: str) -> BaseEngine:
        provider = self._resolver.resolve(EXECUTION_ENGINE_REQUIREMENT)
        return provider.create(provider_id)


def resolve_execution_engine_resolver() -> ExecutionEnginePluginResolver:
    """Resolve the execution engine resolver from environment configuration.

        中文：根据环境配置解析执行引擎解析器。"""
    profile_str = os.environ.get("CYRENE_SERVING_PROFILE", "").strip().upper()
    connection_ref = os.environ.get("CYRENE_SERVING_CONNECTION_REF")
    provider_id = os.environ.get("CYRENE_SERVING_PROVIDER_ID")

    # Production defaults to direct Plugin binding. Compatibility is never
    # selected implicitly by a missing environment variable.
    # 生产默认直连插件；缺少环境变量绝不隐式启用兼容引擎。
    if not profile_str:
        profile_str = ServingProfile.DIRECT_PLUGIN.value

    if profile_str == ServingProfile.DIRECT_PLUGIN.value:
        binding = ExecutionEngineBinding(
            profile=ServingProfile.DIRECT_PLUGIN,
            connection_ref=connection_ref,
            provider_id=provider_id,
        )
        return ConfiguredExecutionEngineResolver(binding=binding)

    raise ServingPortFailure(
        f"SERVING_PROFILE_UNSUPPORTED: unknown serving profile {profile_str!r}",
        status=500,
    )


__all__ = [
    "EXECUTION_ENGINE_CAPABILITY",
    "EXECUTION_ENGINE_INTERFACE_VERSION",
    "EXECUTION_ENGINE_REQUIREMENT",
    "EXECUTION_ENGINE_TYPE_URL_PREFIX",
    "ConfiguredExecutionEngineResolver",
    "DirectPluginEngineProvider",
    "DirectPluginExecutionEngineAdapter",
    "ExecutionEngineBinding",
    "ExecutionEngineCapabilityFactory",
    "ExecutionEnginePluginResolver",
    "ExecutionEnginePort",
    "ExecutionEngineProvider",
    "ExecutionEngineRequirement",
    "ServingPortFailure",
    "ServingProfile",
    "resolve_execution_engine_resolver",
]
