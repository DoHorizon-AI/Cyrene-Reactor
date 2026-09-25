"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 domain.py                                                       │
│  Module: cyrene_reactor_product.domain                              │
│  Role: Product-owned Deployment and Endpoint boundary models.       │
│                                                                     │
│  模块职责：定义 Deployment 与 Endpoint 的独立产品契约。                   │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from cyrene_yield_contracts import ModelVersion
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


def utc_now() -> datetime:
    """Return a timezone-aware timestamp. | 返回带时区时间。"""

    return datetime.now(UTC)


ModelVersionDocument = dict[str, Any]


def canonical_model_version(value: Mapping[str, Any]) -> ModelVersionDocument:
    """Validate through the Yield ModelVersion SDK and return its wire form.

    Reactor stores the canonical Yield document as opaque Product state. It
    deliberately does not reimplement ModelVersion identity or lineage rules.

        中文:通过 Yield ModelVersion SDK 验证,并返回其 wire 格式。

            中文：Reactor 将 Yield 规范文档作为不透明的 Product 状态保存,
            不会重新实现 ModelVersion 标识或血缘规则。
    """

    try:
        payload = dict(value)
        model_version = (
            ModelVersion.from_dict(payload) if "id" in payload else ModelVersion.create(payload)
        )
        document = model_version.to_dict()
        if not isinstance(document, dict) or not isinstance(document.get("id"), str):
            raise ValueError("missing canonical id")
        if document.get("composition") not in {"FULL_MODEL", "BASE_PLUS_LORA"}:
            raise ValueError("unsupported composition")
        return dict(document)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("MODEL_VERSION_INVALID: Yield ModelVersion validation failed") from exc


def model_version_artifact(document: Mapping[str, Any]) -> ArtifactRef:
    """Return the serving ArtifactRef projection for a canonical version.

        中文:返回规范版本对应的服务 ArtifactRef 投影。"""

    composition = document.get("composition")
    if composition == "FULL_MODEL":
        value = document.get("fullModelArtifact")
    elif composition == "BASE_PLUS_LORA":
        base_model = document.get("baseModel")
        value = base_model.get("artifact") if isinstance(base_model, Mapping) else None
    else:
        value = None
    if not isinstance(value, Mapping):
        raise ValueError("MODEL_VERSION_INVALID: serving artifact is missing")
    return ArtifactRef.model_validate(dict(value))


class ContractModel(BaseModel):
    """Stable camelCase wire model. | 稳定 camelCase 线格式模型。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class DesiredState(StrEnum):
    """User-owned Deployment intent. | 用户声明的 Deployment 意图。"""

    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"


class ObservedState(StrEnum):
    """Reactor-owned reconciled Deployment observation. | Reactor 观测状态。"""

    STARTING = "STARTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


class DeploymentPhase(StrEnum):
    """Granular phase in Deployment execution timeline. | 部署执行阶段。"""

    QUEUED = "QUEUED"
    IMPORTING = "IMPORTING"
    LOADING = "LOADING"
    PROBING = "PROBING"
    READY = "READY"
    STOPPING = "STOPPING"
    RELEASED = "RELEASED"
    FAILED = "FAILED"


class DeploymentEvent(ContractModel):
    """Timestamped phase event for a deployment. | 部署阶段事件。"""

    sequence: int = Field(ge=1)
    phase: DeploymentPhase
    message: str
    occurred_at: datetime
    failure_code: str | None = None


class DeploymentEventsResponse(ContractModel):
    """Historical list of phase events for a deployment. | 部署阶段事件列表。"""

    deployment_id: UUID
    events: list[DeploymentEvent]


DiagnosticSource = Literal["product", "trainer", "runtime", "platform"]
DiagnosticStream = Literal["stdout", "stderr", "combined"]
DiagnosticLevel = Literal["debug", "info", "warn", "error"]


class DiagnosticRecord(ContractModel):
    """One redacted diagnostic line a console may show verbatim.

        中文:控制台可以原样展示的一条脱敏诊断记录。"""

    sequence: int = Field(ge=1)
    timestamp: str
    level: DiagnosticLevel = "info"
    source: DiagnosticSource = "product"
    stream: DiagnosticStream = "combined"
    code: str | None = Field(default=None, max_length=200)
    message: str = Field(default="", max_length=8192)
    request_id: str | None = Field(default=None, max_length=200)
    operation_id: str | None = Field(default=None, max_length=200)
    resource_id: str | None = Field(default=None, max_length=200)
    attempt_id: str | None = Field(default=None, max_length=200)
    truncated: bool = False


class DiagnosticsPage(ContractModel):
    """One page of diagnostics for a single Deployment. | 部署诊断分页。"""

    resource_id: str
    items: list[DiagnosticRecord] = Field(default_factory=list)
    next_sequence: int = Field(ge=0)
    terminal: bool = False
    diagnostics_degraded: bool = False


class ModelComposition(StrEnum):
    """Supported immutable serving composition. | 支持的不可变模型组合。"""

    FULL_MODEL = "FULL_MODEL"
    BASE_PLUS_LORA = "BASE_PLUS_LORA"


class EndpointState(StrEnum):
    """Endpoint lifecycle independent of Deployment intent. | Endpoint 生命周期。"""

    PROVISIONING = "PROVISIONING"
    READY = "READY"
    UNHEALTHY = "UNHEALTHY"
    RETIRED = "RETIRED"


class ArtifactRef(ContractModel):
    """Generated projection of the canonical Platform ArtifactRef. | 平台制品引用投影。"""

    model_config = ConfigDict(
        alias_generator=None,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )

    uri: str = Field(pattern=r"^artifact://sha256/[0-9a-f]{64}$")
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    kind: Literal[
        "generic",
        "model",
        "dataset",
        "checkpoint",
        "training_spec",
        "metrics",
        "merged",
        "quantized",
        "report",
    ]
    manifest_digest: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )


class ProductFailure(ContractModel):
    """Failure persisted on Deployment state. | Deployment 持久化失败。"""

    code: str
    message: str
    retryable: bool


class NodeRef(ContractModel):
    """Projection of the canonical Node identity and epoch. | 节点身份与纪元投影。"""

    node_id: str = Field(min_length=1, max_length=200)
    node_epoch: int = Field(gt=0)


class RestartRequest(ContractModel):
    """Restart requires refreshed identity and current Product version. | 重启确认。"""

    node_ref: NodeRef
    resource_version: int = Field(gt=0)


class ModelImportSourceKind(StrEnum):
    """Admitted external model source kinds. | 允许的外部模型来源类型。"""

    HUGGING_FACE = "HUGGING_FACE"
    LOCAL_PATH = "LOCAL_PATH"


class ModelImportSource(ContractModel):
    """Immutable external model source, independent of producer Product. | 外部模型来源。"""

    kind: ModelImportSourceKind
    repository: str | None = Field(default=None, min_length=1, max_length=300)
    revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    path: str | None = Field(default=None, min_length=1, max_length=4096)

    @model_validator(mode="after")
    def validate_source(self) -> ModelImportSource:
        if self.kind == ModelImportSourceKind.HUGGING_FACE:
            if not self.repository or "/" not in self.repository:
                raise ValueError("MODEL_IMPORT_SOURCE_INVALID: repository must be owner/name")
            if self.revision is None:
                raise ValueError(
                    "MODEL_IMPORT_SOURCE_INVALID: a pinned 40-hex revision is required"
                )
            if self.path is not None:
                raise ValueError(
                    "MODEL_IMPORT_SOURCE_INVALID: a Hugging Face source cannot have a path"
                )
            return self
        if not self.path or not self.path.startswith("/"):
            raise ValueError(
                "MODEL_IMPORT_SOURCE_INVALID: a local import requires an absolute path"
            )
        segments = Path(self.path).parts
        if ".." in segments:
            raise ValueError("MODEL_IMPORT_SOURCE_INVALID: path traversal is not admitted")
        if self.repository is not None or self.revision is not None:
            raise ValueError("MODEL_IMPORT_SOURCE_INVALID: a local source cannot have a repository")
        return self


class ModelImportState(StrEnum):
    """Reactor-owned ModelImport lifecycle. | 模型导入生命周期。"""

    VALIDATING = "VALIDATING"
    READY = "READY"
    FAILED = "FAILED"


class ModelImportValidation(ContractModel):
    """Validation evidence returned by the serving binding. | 服务绑定返回的校验证据。"""

    weights: bool
    config: bool
    tokenizer: bool
    chat_template: bool
    license: str | None = Field(default=None, exclude_if=lambda value: value is None)
    provenance: str = Field(min_length=1)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trust_remote_code: Literal[False] = False
    issues: list[str] = Field(default_factory=list)


class ModelImportResult(ContractModel):
    """Validated model artifact published by the binding. | 绑定发布的已校验模型制品。"""

    model_artifact: ArtifactRef
    validation: ModelImportValidation


class ModelImport(ContractModel):
    """Persisted import independent of any Deployment. | 独立于 Deployment 的持久化导入。"""

    id: UUID
    name: str = Field(min_length=1, max_length=200)
    serving_binding_id: str = Field(min_length=1, max_length=200)
    source: ModelImportSource
    credential_ref: str | None = Field(
        default=None, min_length=1, max_length=300, exclude_if=lambda value: value is None
    )
    state: ModelImportState
    model_artifact: ArtifactRef | None = None
    validation: ModelImportValidation | None = None
    failure: ProductFailure | None = None
    created_at: datetime
    updated_at: datetime
    resource_version: int = Field(ge=1)


class CreateModelImportRequest(ContractModel):
    """Create-ModelImport command. | 创建模型导入请求。"""

    name: str = Field(min_length=1, max_length=200)
    serving_binding_id: str = Field(min_length=1, max_length=200)
    source: ModelImportSource
    credential_ref: str | None = Field(default=None, min_length=1, max_length=300)
    trust_remote_code: bool = False


class Deployment(ContractModel):
    """Durable Product deployment intent and observation. | 持久化部署意图与观测。"""

    id: UUID
    name: str = Field(min_length=1, max_length=200)
    model_artifact: ArtifactRef | None = None
    composition: ModelComposition = ModelComposition.FULL_MODEL
    model_version: ModelVersionDocument | None = None
    desired_state: DesiredState
    observed_state: ObservedState
    serving_binding_id: str = Field(min_length=1, max_length=200)
    node_ref: NodeRef | None = None
    serving_capability_type: Literal["execution.engine.v1"] = "execution.engine.v1"
    endpoint_id: UUID | None = None
    failure: ProductFailure | None = None
    created_at: datetime
    updated_at: datetime
    resource_version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_model_identity(self) -> Deployment:
        if self.model_version is None:
            if self.composition != ModelComposition.FULL_MODEL or self.model_artifact is None:
                raise ValueError(
                    "MODEL_VERSION_REQUIRED: composed deployments require modelVersion"
                )
            return self
        canonical = canonical_model_version(self.model_version)
        version_composition = ModelComposition(canonical["composition"])
        if version_composition != self.composition:
            raise ValueError("MODEL_COMPOSITION_MISMATCH: deployment and modelVersion disagree")
        projection = model_version_artifact(canonical)
        if self.model_artifact is not None and self.model_artifact != projection:
            raise ValueError("MODEL_ARTIFACT_MISMATCH: modelArtifact must match modelVersion")
        self.model_version = canonical
        self.model_artifact = projection
        return self


class Endpoint(ContractModel):
    """Addressable serving surface, separate from Deployment. | 独立可寻址服务面。"""

    id: UUID
    deployment_id: UUID
    state: EndpointState
    url: str
    model: str | None = Field(default=None, min_length=1, exclude_if=lambda value: value is None)
    protocol: Literal["openai.chat.v1"] = "openai.chat.v1"
    created_at: datetime
    updated_at: datetime
    resource_version: int = Field(ge=1)


class CreateDeploymentRequest(ContractModel):
    """Create-Deployment command. | 创建 Deployment 请求。"""

    name: str = Field(min_length=1, max_length=200)
    model_artifact: ArtifactRef | None = None
    composition: ModelComposition = ModelComposition.FULL_MODEL
    model_version: ModelVersionDocument | None = None
    serving_binding_id: str = Field(min_length=1, max_length=200)
    node_ref: NodeRef | None = None

    @model_validator(mode="after")
    def validate_model_identity(self) -> CreateDeploymentRequest:
        if self.model_version is None:
            if self.composition != ModelComposition.FULL_MODEL or self.model_artifact is None:
                raise ValueError(
                    "MODEL_VERSION_REQUIRED: composed deployments require modelVersion"
                )
            return self
        canonical = canonical_model_version(self.model_version)
        version_composition = ModelComposition(canonical["composition"])
        # The default FULL_MODEL keeps old request bodies valid. A supplied
        # composed ModelVersion is the only authority when that default is
        # present; an explicit composed composition must still agree.
        # 中文：默认 FULL_MODEL 可继续接受旧版请求体。当请求提供组合 ModelVersion 时,它是唯一权威;
        # 若显式指定了组合类型,其值仍必须一致。
        if (
            self.composition == ModelComposition.FULL_MODEL
            and version_composition == ModelComposition.BASE_PLUS_LORA
        ):
            if "composition" in self.model_fields_set:
                raise ValueError("MODEL_COMPOSITION_MISMATCH: request and modelVersion disagree")
            self.composition = version_composition
        elif version_composition != self.composition:
            raise ValueError("MODEL_COMPOSITION_MISMATCH: request and modelVersion disagree")
        projection = model_version_artifact(canonical)
        if self.model_artifact is not None and self.model_artifact != projection:
            raise ValueError("MODEL_ARTIFACT_MISMATCH: modelArtifact must match modelVersion")
        self.model_version = canonical
        self.model_artifact = projection
        return self


class EngineHandle(ContractModel):
    """Opaque evidence returned by a serving engine. | 服务引擎返回的不透明证据。"""

    execution_ref: str
    endpoint_url: str
    model: str | None = None
    model_version_id: str | None = None


class ProductResourceRef(ContractModel):
    """Cross-Product reference without producer business state. | 跨产品资源引用。"""

    uri: str = Field(pattern=r"^(cyrene|https?)://", max_length=2000)
    id: UUID
    resource_version: int = Field(ge=1)


class CreateDeploymentDraft(ContractModel):
    """Import a canonical version; no execution intent is implied. | 导入部署草稿。"""

    source_ref: ProductResourceRef
    model_version: ModelVersionDocument

    @model_validator(mode="after")
    def validate_version(self) -> CreateDeploymentDraft:
        self.model_version = canonical_model_version(self.model_version)
        return self


class DeploymentDraft(CreateDeploymentDraft):
    """Reactor-owned preparation before explicit deployment. | 显式部署前的准备资源。"""

    id: UUID
    resource_ref: ProductResourceRef
    state: Literal["DRAFT", "STARTED"] = "DRAFT"
    deployment_ref: ProductResourceRef | None = None
    created_at: datetime


class DeployDraftRequest(ContractModel):
    """User-selected serving destination for an imported draft. | 用户选择部署目标。"""

    name: str = Field(min_length=1, max_length=200)
    serving_binding_id: str = Field(min_length=1, max_length=200)
    node_ref: NodeRef | None = None


class SendToExchangeRequest(ContractModel):
    """Explicit receiver draft intent bound to an inspected Endpoint. | 显式发送草稿。"""

    resource_version: int = Field(ge=1)
    receiver_id: str = Field(min_length=1, max_length=200)
    gateway_endpoint_id: UUID
    target_binding_id: str = Field(min_length=1, max_length=300)
    model_pattern: str = Field(min_length=1, max_length=200)
    priority: int = Field(default=100, ge=0, le=10_000)


class EngineObservation(ContractModel):
    """Identity-checked serving observation. | 已校验身份的服务观测。"""

    ready: bool
    detail: str


class ProblemDetails(ContractModel):
    """RFC 9457 response with stable Reactor extensions. | RFC 9457 错误响应。"""

    type: str
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    instance: str
    code: str
    retryable: bool
    trace_id: str
    resource_ref: str | None = None
    request_id: str | None = None
    recovery_action: str | None = None
