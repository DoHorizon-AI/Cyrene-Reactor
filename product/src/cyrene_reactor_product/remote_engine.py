"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 remote_engine.py                                                │
│  Module: cyrene_reactor_product.remote_engine                       │
│  Role: Consume an existing serving binding over authenticated HTTP.│
│  模块职责：产品侧远程服务适配，验证控制回复及实际可达的推理接口。             │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict

from cyrene_reactor_product.domain import (
    ArtifactRef,
    CreateModelImportRequest,
    EngineHandle,
    EngineObservation,
    ModelImportResult,
    ModelImportValidation,
    ModelVersionDocument,
    NodeRef,
    canonical_model_version,
    model_version_artifact,
)
from cyrene_reactor_product.errors import ServingEngineFailure


class ServingBindingConfiguration(BaseModel):
    """Operator-provided binding; secrets and private paths are never exported. | 绑定配置。"""

    model_config = ConfigDict(extra="forbid")
    binding_id: str
    control_url: str
    credential_file: Path


def _validate_model_version_readback(
    result: dict[str, Any], expected: ModelVersionDocument, model: ArtifactRef
) -> ModelVersionDocument:
    """Canonicalize host readback and verify both composed identity projections.

    中文:规范化主机回读结果,并验证组合模型的两种身份投影。"""

    returned = result.get("modelVersion")
    if not isinstance(returned, dict):
        raise ValueError("MODEL_VERSION_READBACK_MISSING")
    canonical = canonical_model_version(returned)
    expected_canonical = canonical_model_version(expected)
    if canonical["id"] != expected_canonical["id"]:
        raise ValueError("MODEL_VERSION_IDENTITY_MISMATCH")
    if model_version_artifact(expected_canonical) != model:
        raise ValueError("MODEL_VERSION_BASE_PROJECTION_MISMATCH")
    if model_version_artifact(canonical) != model:
        raise ValueError("MODEL_VERSION_BASE_PROJECTION_MISMATCH")
    returned_artifact = ArtifactRef.model_validate(result.get("modelArtifact"))
    if returned_artifact != model:
        raise ValueError("MODEL_ARTIFACT_IDENTITY_MISMATCH")
    return canonical


def _canonical_expected_model_version(
    value: dict[str, Any], model: ArtifactRef
) -> ModelVersionDocument:
    """Validate a composed request before sending it to a remote host.

    中文:向远程主机发送组合模型请求之前先进行验证。"""

    canonical = canonical_model_version(value)
    if model_version_artifact(canonical) != model:
        raise ValueError("MODEL_VERSION_BASE_PROJECTION_MISMATCH")
    return canonical


class RemoteServingExecutionPort:
    """Support physically separate Product control and CUDA execution hosts. | 远程服务端口。"""

    def __init__(self, binding: ServingBindingConfiguration) -> None:
        self.binding = binding
        self.token = binding.credential_file.read_text().strip()
        if len(self.token) < 32 or binding.credential_file.stat().st_mode & 0o077:
            raise ValueError("SERVING_CREDENTIAL_INVALID")
        parsed = urlsplit(binding.control_url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("SERVING_URL_INVALID")
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        ):
            raise ValueError(
                "SERVING_TLS_REQUIRED: remote bindings require HTTPS or a local SSH tunnel"
            )

    def import_model(self, command: CreateModelImportRequest) -> ModelImportResult:
        """Ask the binding to validate and publish the external source. | 委托校验与发布。"""

        payload: dict[str, Any] = {
            "name": command.name,
            "source": command.source.model_dump(mode="json", by_alias=True, exclude_none=True),
            "trustRemoteCode": False,
        }
        if command.credential_ref is not None:
            payload["credentialRef"] = command.credential_ref
        result = self.request("POST", "/imports", payload)
        try:
            artifact = ArtifactRef.model_validate(result["modelArtifact"])
            validation = ModelImportValidation.model_validate(result["validation"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ServingEngineFailure(
                "SERVING_RESPONSE_INCOMPATIBLE: the binding returned invalid import evidence",
                status=409,
            ) from exc
        return ModelImportResult(model_artifact=artifact, validation=validation)

    def request(self, method: str, path: str, payload: Any = None) -> dict[str, Any]:
        """Call the selected binding with bounded timeout and explicit errors. | 调用选定绑定。"""
        try:
            timeout = 1900 if method == "POST" and not path.endswith("/stop") else 45
            with httpx.Client(timeout=httpx.Timeout(timeout, connect=5), trust_env=False) as client:
                response = client.request(
                    method,
                    self.binding.control_url.rstrip("/") + path,
                    json=payload,
                    headers={"Authorization": "Bearer " + self.token},
                )
                body = response.json()
                if not isinstance(body, dict):
                    raise ValueError("SERVING_RESPONSE_INCOMPATIBLE")
                if response.is_error:
                    status = response.status_code
                    code = (
                        "SERVING_BINDING_PERMISSION_DENIED"
                        if status in {401, 403}
                        else str(body.get("code", "SERVING_REQUEST_FAILED"))
                    )
                    raise ServingEngineFailure(
                        code + ": " + str(body.get("detail", "Refresh the binding and retry")),
                        status=403 if status in {401, 403} else status,
                        retryable=bool(body.get("retryable", status >= 500)),
                    )
                return body
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ServingEngineFailure(
                "SERVING_BINDING_UNREACHABLE: refresh the node and retry",
                status=503,
                retryable=True,
            ) from exc

    def prepare(self, deployment_id: UUID) -> EngineHandle:
        """Reserve only a stable handle, not resources or a runnable state. | 预留恢复身份。"""
        return EngineHandle(
            execution_ref=str(deployment_id),
            endpoint_url=self.binding.control_url.rstrip("/") + f"/serving/{deployment_id}/v1",
            model="reactor-" + str(deployment_id),
        )

    def start(
        self,
        deployment_id: UUID,
        model: ArtifactRef,
        *,
        node_ref: NodeRef | None = None,
        model_version: dict[str, Any] | None = None,
    ) -> EngineHandle:
        """Confirm the node and verify both network paths. | 确认后部署。"""
        if node_ref is None:
            raise ServingEngineFailure("NODE_CONFIRMATION_REQUIRED: select a node from the binding")
        expected_version: ModelVersionDocument | None = None
        if model_version is not None:
            try:
                expected_version = _canonical_expected_model_version(model_version, model)
            except (TypeError, ValueError) as exc:
                raise ServingEngineFailure(
                    "MODEL_VERSION_INVALID: composed model does not match its base artifact",
                    status=422,
                ) from exc
        try:
            payload: dict[str, Any] = {
                "modelArtifact": model.model_dump(mode="json"),
                "nodeRef": node_ref.model_dump(mode="json"),
            }
            if expected_version is not None:
                payload["modelVersion"] = expected_version
            result = self.request(
                "POST",
                f"/executions/{deployment_id}",
                payload,
            )
        except ServingEngineFailure as exc:
            raise ServingEngineFailure(
                str(exc),
                execution_ref=str(deployment_id),
                endpoint_url=self.binding.control_url.rstrip("/") + f"/serving/{deployment_id}/v1",
                status=exc.status,
                retryable=exc.retryable,
            ) from exc
        if result.get("ready") is not True:
            raise ServingEngineFailure(
                "MODEL_NOT_READY: " + str(result.get("detail", "incompatible host response")),
                execution_ref=str(deployment_id),
                endpoint_url=self.prepare(deployment_id).endpoint_url,
                status=503,
                retryable=True,
            )
        try:
            returned_version_id: str | None = None
            if expected_version is not None:
                returned_version = _validate_model_version_readback(result, expected_version, model)
                returned_version_id = returned_version["id"]
            handle = EngineHandle(
                execution_ref=str(deployment_id),
                endpoint_url=result["endpointUrl"],
                model=result["servedModel"],
                model_version_id=returned_version_id,
            )
            if handle.model != "reactor-" + str(deployment_id):
                raise ServingEngineFailure(
                    "MODEL_IDENTITY_MISMATCH: the binding returned an unexpected served model",
                    execution_ref=handle.execution_ref,
                    endpoint_url=handle.endpoint_url,
                    status=409,
                )
        except (ValueError, KeyError, TypeError) as exc:
            raise ServingEngineFailure(
                "SERVING_RESPONSE_INCOMPATIBLE: restore the binding before retrying",
                execution_ref=str(deployment_id),
                endpoint_url=self.prepare(deployment_id).endpoint_url,
                status=409,
            ) from exc
        observation = self.inspect(
            handle.execution_ref,
            handle.endpoint_url,
            deployment_id,
            expected_version["id"] if expected_version is not None else model.digest,
            model_version=expected_version,
        )
        if not observation.ready:
            # Startup succeeded remotely; keep its opaque identity for explicit stop/recovery.
            # 服务已启动,但产品侧数据通路不通时不允许宣称 READY。
            raise ServingEngineFailure(
                "INFERENCE_DATA_PATH_UNREACHABLE: stop or repair binding reachability",
                execution_ref=handle.execution_ref,
                endpoint_url=handle.endpoint_url,
                status=503,
                retryable=True,
            )
        return handle

    def verify_served_model(
        self,
        deployment_id: UUID,
        execution_ref: str,
        endpoint_url: str,
        served_model: str | None,
    ) -> None:
        """Verify the OpenAI model registry after startup. | 启动后校验模型注册表。"""

        expected_model = "reactor-" + str(deployment_id)
        if execution_ref != str(deployment_id) or served_model != expected_model:
            raise ServingEngineFailure(
                "MODEL_IDENTITY_MISMATCH: the serving handle does not match the deployment",
                execution_ref=execution_ref,
                endpoint_url=endpoint_url,
                status=409,
            )
        endpoint = urlsplit(endpoint_url)
        binding = urlsplit(self.binding.control_url)
        if endpoint.scheme != binding.scheme or endpoint.netloc != binding.netloc:
            raise ServingEngineFailure(
                "INFERENCE_ORIGIN_NOT_ADMITTED: the serving endpoint is outside its binding",
                execution_ref=execution_ref,
                endpoint_url=endpoint_url,
                status=409,
            )
        try:
            with httpx.Client(timeout=30, trust_env=False) as client:
                response = client.get(
                    endpoint_url.rstrip("/") + "/models",
                    headers={"Authorization": "Bearer " + self.token},
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            raise ServingEngineFailure(
                "INFERENCE_DATA_PATH_UNREACHABLE: serving model readback is unavailable",
                execution_ref=execution_ref,
                endpoint_url=endpoint_url,
                status=503,
                retryable=True,
            ) from exc
        except (TypeError, ValueError) as exc:
            raise ServingEngineFailure(
                "SERVING_RESPONSE_INCOMPATIBLE: serving model readback is not valid JSON",
                execution_ref=execution_ref,
                endpoint_url=endpoint_url,
                status=409,
            ) from exc

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list) or not any(
            isinstance(item, dict) and item.get("id") == expected_model for item in data
        ):
            raise ServingEngineFailure(
                "MODEL_IDENTITY_MISMATCH: /v1/models did not advertise the intended served model",
                execution_ref=execution_ref,
                endpoint_url=endpoint_url,
                status=409,
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
        """Verify inference from the control host. | 跨机验证。"""
        if execution_ref != str(deployment_id):
            return EngineObservation(ready=False, detail="EXECUTION_IDENTITY_MISMATCH")
        try:
            result = self.request("GET", f"/executions/{deployment_id}")
            expected_version: ModelVersionDocument | None = None
            if model_version is not None:
                returned_artifact = ArtifactRef.model_validate(result["modelArtifact"])
                expected_version = canonical_model_version(model_version)
                expected_artifact = model_version_artifact(expected_version)
                if expected_artifact != returned_artifact:
                    raise ValueError("MODEL_VERSION_BASE_PROJECTION_MISMATCH")
                _validate_model_version_readback(result, expected_version, expected_artifact)
                identity_matches = expected_version["id"] == model_digest
            else:
                identity_matches = result["modelArtifact"]["digest"] == model_digest
            if (
                result.get("ready") is not True
                or not identity_matches
                or result["endpointUrl"] != endpoint_url
            ):
                return EngineObservation(ready=False, detail=result["detail"])
            # Only the configured binding's origin can receive its credential.
            # 防止远端返回任意地址导致凭据外送。
            if (
                urlsplit(endpoint_url).netloc != urlsplit(self.binding.control_url).netloc
                or urlsplit(endpoint_url).scheme != urlsplit(self.binding.control_url).scheme
            ):
                return EngineObservation(ready=False, detail="INFERENCE_ORIGIN_NOT_ADMITTED")
            with httpx.Client(timeout=30, trust_env=False) as client:
                answer = client.post(
                    endpoint_url + "/chat/completions",
                    headers={"Authorization": "Bearer " + self.token},
                    json={
                        "model": result["servedModel"],
                        "messages": [{"role": "user", "content": "Reply with one word: ready"}],
                        "max_tokens": 8,
                        "temperature": 0,
                    },
                )
                answer.raise_for_status()
                body = answer.json()
                ready = body.get("model") == result["servedModel"] and bool(
                    body["choices"][0]["message"].get("content")
                )
            return EngineObservation(
                ready=ready,
                detail="CONTROL_AND_INFERENCE_VERIFIED" if ready else "MODEL_INFERENCE_EMPTY",
            )
        except (
            ServingEngineFailure,
            httpx.HTTPError,
            KeyError,
            ValueError,
            IndexError,
            TypeError,
            AttributeError,
        ):
            return EngineObservation(ready=False, detail="CONTROL_OR_INFERENCE_UNREACHABLE")

    def diagnostics(
        self, execution_ref: str, *, after_sequence: int = 0, limit: int = 200
    ) -> dict[str, Any] | None:
        """Read the serving process output through the binding.

        A binding that cannot answer (older runtime, transient failure) reports
        None so the Product still returns its own records and marks the page
        degraded instead of failing the request.

            中文:通过绑定读取服务进程输出。

                中文：若绑定无法响应(例如运行时版本较旧或发生临时故障),则返回 None。
                Product 仍会返回自身记录,并将页面标记为降级,而不是让请求失败。
        """

        try:
            page = self.request(
                "GET",
                f"/executions/{execution_ref}/diagnostics"
                f"?afterSequence={int(after_sequence)}&limit={int(limit)}",
            )
        except (ServingEngineFailure, ValueError):
            return None
        return page if isinstance(page.get("items"), list) else None

    def stop(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        """Require Kernel release evidence even if inference is unavailable. | 回收确认。"""
        if execution_ref != str(deployment_id):
            raise ServingEngineFailure("EXECUTION_IDENTITY_MISMATCH")
        if model_version is not None:
            expected_version = _canonical_expected_model_version(
                model_version, model_version_artifact(model_version)
            )
            current = self.request("GET", f"/executions/{deployment_id}")
            if (
                _validate_model_version_readback(
                    current, expected_version, model_version_artifact(expected_version)
                )["id"]
                != model_digest
            ):
                raise ServingEngineFailure("MODEL_VERSION_IDENTITY_MISMATCH")
        result = self.request("POST", f"/executions/{deployment_id}/stop")
        if result.get("released") is not True:
            raise ServingEngineFailure("KERNEL_CLEANUP_INCOMPLETE")
        return EngineObservation(ready=False, detail="KERNEL_RESOURCES_RELEASED")
