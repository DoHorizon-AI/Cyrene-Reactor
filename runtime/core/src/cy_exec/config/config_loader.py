"""Load Reactor Product configuration without probing hardware or selecting engines."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from .models import ModelSpec, WorkerConfig

LOGGER = logging.getLogger("cy_llm.worker.config")

ENV_SERVING_PROVIDER_ID = "CYRENE_SERVING_PROVIDER_ID"
ENV_MODEL_REGISTRY = "CY_LLM_MODEL_REGISTRY"
ENV_MODEL_REGISTRY_PATH = "CY_LLM_MODEL_REGISTRY_PATH"
ENV_DEFAULT_MODEL = "CY_LLM_DEFAULT_MODEL"
ENV_DEFAULT_ADAPTER = "CY_LLM_DEFAULT_ADAPTER"


def _parse_registry_json(payload: str) -> dict[str, ModelSpec]:
    """Parse the Product model registry with a strict, current schema."""

    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Model registry must be a JSON object")
    models_data = data.get("models", data)
    if not isinstance(models_data, dict):
        raise ValueError("Model registry 'models' must be an object")
    return {
        logical_name: ModelSpec.model_validate(spec)
        for logical_name, spec in models_data.items()
    }


def load_model_registry(path: str | None = None) -> dict[str, ModelSpec]:
    """Load model bindings from JSON, a file, or the explicit default fields."""

    if ENV_MODEL_REGISTRY in os.environ:
        return _parse_registry_json(os.environ[ENV_MODEL_REGISTRY])
    registry_path = path or os.environ.get(ENV_MODEL_REGISTRY_PATH)
    if registry_path:
        file_path = Path(registry_path).expanduser()
        if not file_path.is_file():
            raise FileNotFoundError(f"Model registry file not found: {file_path}")
        return _parse_registry_json(file_path.read_text(encoding="utf-8"))
    return {
        "default": ModelSpec(
            model_path=os.environ.get(
                ENV_DEFAULT_MODEL, "deepseek-ai/deepseek-llm-7b-chat"
            ),
            adapter_path=os.environ.get(ENV_DEFAULT_ADAPTER),
        )
    }


def load_worker_config(registry_path: str | None = None) -> WorkerConfig:
    """Load Product coordination and selected Plugin identity."""

    provider_id = os.environ.get(ENV_SERVING_PROVIDER_ID, "").strip()
    if not provider_id:
        raise ValueError(f"{ENV_SERVING_PROVIDER_ID} must be non-empty")
    config = WorkerConfig(
        provider_id=provider_id,
        model_registry=load_model_registry(registry_path),
    )
    LOGGER.info(
        "Worker configuration loaded: provider=%s, models=%s",
        provider_id,
        list(config.model_registry),
    )
    return config


def print_config_help() -> None:
    """Print current Product and direct Plugin configuration fields."""

    print(
        "\n".join(
            (
                "CYRENE_SERVING_PROVIDER_ID    selected Plugin package identity",
                "CYRENE_SERVING_CONNECTION_REF local DirectPluginRuntime endpoint",
                "CY_LLM_MODEL_REGISTRY         JSON model binding registry",
                "CY_LLM_MODEL_REGISTRY_PATH    model binding registry file",
                "CY_LLM_DEFAULT_MODEL          default model path or identifier",
                "CY_LLM_DEFAULT_ADAPTER        optional LoRA adapter path",
            )
        )
    )


__all__ = [
    "ENV_DEFAULT_ADAPTER",
    "ENV_DEFAULT_MODEL",
    "ENV_MODEL_REGISTRY",
    "ENV_MODEL_REGISTRY_PATH",
    "ENV_SERVING_PROVIDER_ID",
    "ModelSpec",
    "WorkerConfig",
    "load_model_registry",
    "load_worker_config",
    "print_config_help",
]
