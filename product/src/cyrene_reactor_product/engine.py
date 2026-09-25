"""Product-owned serving lifecycle port without an in-tree engine implementation.

The port carries Product deployment identity and lifecycle intent. Concrete
model loading, inference, hardware tuning, and provider behavior belong to the
versioned ``execution.engine.v1`` capability in Cyrene-Plugins-Official.

中文:由 Product 所有的服务生命周期端口;仓库内不包含引擎实现。

中文:该端口承载 Product Deployment 标识和生命周期意图。具体模型加载、推理、硬件调优和提供方行为属于 `Cyrene-Plugins-Official` 中有版本的 ``execution.engine.v1`` 能力。
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
    """Product lifecycle port implemented by an externally configured binding.

        中文:由外部配置绑定实现的 Product 生命周期端口。"""

    def import_model(self, command: CreateModelImportRequest) -> ModelImportResult:
        """Validate and publish an external model source through the binding.

            中文:通过绑定验证并发布外部模型源。"""

    def prepare(self, deployment_id: UUID) -> EngineHandle | None:
        """Return stable recovery evidence before any execution mutation.

            中文:在修改执行状态之前返回稳定的恢复证据。"""

    def start(
        self,
        deployment_id: UUID,
        model: ArtifactRef,
        *,
        node_ref: NodeRef | None = None,
        model_version: dict[str, Any] | None = None,
    ) -> EngineHandle:
        """Start serving and return opaque execution evidence.

            中文:启动服务并返回不透明的执行证据。"""

    def inspect(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        """Verify live endpoint identity through the configured binding.

            中文:通过已配置的绑定验证活动端点标识。"""

    def stop(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        """Stop an identity-verified serving execution.

            中文:停止已验证标识的服务执行实例。"""

    def diagnostics(
        self, execution_ref: str, *, after_sequence: int = 0, limit: int = 200
    ) -> dict[str, Any] | None:
        """Read the runtime's own output, or None when the binding cannot report it.

            中文:读取运行时自身的输出;若绑定无法提供,则返回 None。"""


class UnconfiguredServingExecutionPort:
    """Fail closed until an external serving binding is configured.

        中文:在配置外部服务绑定之前按失败即拒绝处理。"""

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

    def diagnostics(
        self, execution_ref: str, *, after_sequence: int = 0, limit: int = 200
    ) -> dict[str, Any] | None:
        # Without a binding there is no runtime output to report; the Product
        # still serves its own records rather than failing the whole page.
        # 中文:没有绑定时就没有运行时输出可报告;Product 仍会提供自身记录,不会让整个页面请求失败。
        del execution_ref, after_sequence, limit
        return None


__all__ = ["ServingExecutionPort", "UnconfiguredServingExecutionPort"]
