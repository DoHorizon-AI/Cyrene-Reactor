"""Product-side configuration models for the Reactor worker.

中文:Reactor 工作器的 Product 侧配置模型。"""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelSpec(BaseModel):
    """One Product model binding projected into a Plugins-owned engine request.

        中文:从单个 Product 模型绑定映射为 Plugins 所有引擎请求的配置。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model_path: str = Field(min_length=1)
    adapter_path: str | None = None
    provider_id: str | None = None
    quantization: str | None = None
    max_model_len: int | None = Field(default=None, ge=1)
    tensor_parallel_size: int | None = Field(default=None, ge=1)
    gpu_memory_utilization: float | None = Field(default=None, gt=0.0, le=1.0)
    enable_prefix_caching: bool | None = None
    kv_cache_dtype: str | None = None


class WorkerConfig(BaseModel):
    """Reactor coordination configuration without hardware or engine authority.

        中文:Reactor 协调配置,不包含硬件或引擎权威。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_id: str = Field(min_length=1)
    model_registry: Dict[str, ModelSpec] = Field(default_factory=dict)
    grpc_port: int = Field(default=50051, ge=1, le=65535)
    max_workers: int = Field(default=10, ge=1)
    queue_size: int = Field(default=128, ge=1)


class ServerConfig(BaseModel):
    """Product server configuration.

        中文:Product 服务器配置。"""

    host: str = "0.0.0.0"
    port: int = Field(default=50051, ge=1, le=65535)
    grpc_max_workers: int = Field(default=10, ge=1)
    grpc_max_message_size: int = Field(default=100 * 1024 * 1024, ge=1)
    grpc_keepalive_time_ms: int = Field(default=30000, ge=1)
    grpc_keepalive_timeout_ms: int = Field(default=10000, ge=1)
    enable_auth: bool = True
    internal_token: str | None = None


class WorkerSettings(BaseSettings):
    """Environment projection for Product and Plugin binding configuration.

        中文:Product 和 Plugin 绑定配置的环境变量投影。"""

    provider_id: str | None = Field(default=None, alias="CYRENE_SERVING_PROVIDER_ID")
    model_registry: str | None = Field(default=None, alias="CY_LLM_MODEL_REGISTRY")
    model_registry_path: str | None = Field(default=None, alias="CY_LLM_MODEL_REGISTRY_PATH")
    default_model: str = Field(
        default="deepseek-ai/deepseek-llm-7b-chat",
        alias="CY_LLM_DEFAULT_MODEL",
    )
    default_adapter: str | None = Field(default=None, alias="CY_LLM_DEFAULT_ADAPTER")
    port: int = Field(default=50051, alias="CY_LLM_PORT")
    internal_token: str | None = Field(default=None, alias="CY_LLM_INTERNAL_TOKEN")

    model_config = SettingsConfigDict(
        env_prefix="CY_LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


__all__ = ["ModelSpec", "ServerConfig", "WorkerConfig", "WorkerSettings"]
