"""Closed, browser-safe projections for private Workspace routes.

私有 Workspace 路由使用闭合且适合浏览器展示的响应投影。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from cyrene_reactor_product.domain import (
    ArtifactRef,
    ContractModel,
    ModelImport,
    ModelImportSourceKind,
)


class WorkspaceArtifactProjection(ContractModel):
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
    manifest_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")


class WorkspaceModelImportSourceProjection(ContractModel):
    kind: ModelImportSourceKind
    revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


class WorkspaceModelImportValidationProjection(ContractModel):
    weights: bool
    config: bool
    tokenizer: bool
    chat_template: bool
    license: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9.+-]{1,100}$",
    )
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trust_remote_code: Literal[False] = False


class WorkspaceModelImportFailureProjection(ContractModel):
    code: str = Field(pattern=r"^[A-Z0-9_]{1,100}$")
    retryable: bool


class WorkspaceModelImportProjection(ContractModel):
    id: UUID
    name: str = Field(min_length=1, max_length=200, pattern=r"^[^/\\:]{1,200}$")
    serving_binding_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")
    source: WorkspaceModelImportSourceProjection
    state: Literal["VALIDATING", "READY", "FAILED"]
    model_artifact: WorkspaceArtifactProjection | None = None
    validation: WorkspaceModelImportValidationProjection | None = None
    failure: WorkspaceModelImportFailureProjection | None = None
    created_at: datetime
    updated_at: datetime
    resource_version: int = Field(ge=1)


_SCHEME_OR_ABSOLUTE_PATH = re.compile(r"(?i)(?:^[a-z][a-z0-9+.-]*://|^[/\\]|^[a-z]:[/\\])")
_SAFE_FAILURE_CODE = re.compile(r"^[A-Z0-9_]{1,100}$")
_SAFE_DISPLAY_LABEL = re.compile(r"^[^/\\:]{1,200}$")


def _artifact_projection(artifact: ArtifactRef | None) -> WorkspaceArtifactProjection | None:
    if artifact is None:
        return None
    return WorkspaceArtifactProjection(
        digest=artifact.digest,
        size_bytes=artifact.size_bytes,
        kind=artifact.kind,
        manifest_digest=artifact.manifest_digest,
    )


def project_workspace_model_import(model_import: ModelImport) -> WorkspaceModelImportProjection:
    source = model_import.source
    validation = model_import.validation
    failure = model_import.failure
    name = model_import.name
    if _SCHEME_OR_ABSOLUTE_PATH.search(name) or not _SAFE_DISPLAY_LABEL.fullmatch(name):
        name = f"Model import {model_import.id}"
    return WorkspaceModelImportProjection(
        id=model_import.id,
        name=name,
        serving_binding_id=model_import.serving_binding_id,
        source=WorkspaceModelImportSourceProjection(kind=source.kind, revision=source.revision),
        state=model_import.state,
        model_artifact=_artifact_projection(model_import.model_artifact),
        validation=(
            WorkspaceModelImportValidationProjection(
                weights=validation.weights,
                config=validation.config,
                tokenizer=validation.tokenizer,
                chat_template=validation.chat_template,
                license=(
                    validation.license
                    if validation.license is not None
                    and re.fullmatch(r"[A-Za-z0-9.+-]{1,100}", validation.license)
                    else None
                ),
                digest=validation.digest,
                trust_remote_code=validation.trust_remote_code,
            )
            if validation is not None
            else None
        ),
        failure=(
            WorkspaceModelImportFailureProjection(
                code=(
                    failure.code
                    if _SAFE_FAILURE_CODE.fullmatch(failure.code)
                    else "MODEL_IMPORT_FAILED"
                ),
                retryable=failure.retryable,
            )
            if failure is not None
            else None
        ),
        created_at=model_import.created_at,
        updated_at=model_import.updated_at,
        resource_version=model_import.resource_version,
    )
