"""Product-owned serving lifecycle port without an in-tree engine implementation.

The port carries Product deployment identity and lifecycle intent. Concrete
model loading, inference, hardware tuning, and provider behavior belong to the
versioned ``execution.engine.v1`` capability in Cyrene-Plugins-Official.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from cyrene_reactor_product.domain import (
    ArtifactRef,
    CreateModelImportRequest,
    EngineHandle,
    EngineObservation,
    ModelImportResult,
    NodeRef,
)
from cyrene_reactor_product.errors import ServingEngineFailure


class ServingExecutionPort(Protocol):
    """Product lifecycle port implemented by an externally configured binding."""

    def import_model(self, command: CreateModelImportRequest) -> ModelImportResult:
        """Validate and publish an external model source through the binding."""

    def prepare(self, deployment_id: UUID) -> EngineHandle | None:
        """Return stable recovery evidence before any execution mutation."""

    def start(
        self,
        deployment_id: UUID,
        model: ArtifactRef,
        *,
        node_ref: NodeRef | None = None,
        model_version: dict[str, Any] | None = None,
    ) -> EngineHandle:
        """Start serving and return opaque execution evidence."""

    def inspect(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        """Verify live endpoint identity through the configured binding."""

    def stop(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        """Stop an identity-verified serving execution."""


class UnconfiguredServingExecutionPort:
    """Fail closed until an external serving binding is configured."""

    def import_model(self, command: CreateModelImportRequest) -> ModelImportResult:
        del command
        raise ServingEngineFailure(
            "SERVING_BINDING_REQUIRED: configure an external execution.engine.v1 binding"
        )

    def prepare(self, deployment_id: UUID) -> EngineHandle | None:
        del deployment_id
        return None

    def start(
        self,
        deployment_id: UUID,
        model: ArtifactRef,
        *,
        node_ref: NodeRef | None = None,
        model_version: dict[str, Any] | None = None,
    ) -> EngineHandle:
        del deployment_id, model, node_ref, model_version
        raise ServingEngineFailure(
            "SERVING_BINDING_REQUIRED: configure an external execution.engine.v1 binding"
        )

    def inspect(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        del execution_ref, endpoint_url, deployment_id, model_digest, model_version
        return EngineObservation(ready=False, detail="SERVING_BINDING_REQUIRED")

    def stop(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        del execution_ref, endpoint_url, deployment_id, model_digest, model_version
        raise ServingEngineFailure(
            "SERVING_BINDING_REQUIRED: restore the original binding to release resources"
        )


__all__ = ["ServingExecutionPort", "UnconfiguredServingExecutionPort"]
