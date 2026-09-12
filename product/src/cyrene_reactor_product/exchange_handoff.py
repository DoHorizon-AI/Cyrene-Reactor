"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 exchange_handoff.py                                            │
│  Module: cyrene_reactor_product.exchange_handoff                    │
│  Role: Send a versioned Endpoint to an existing Exchange draft API.│
│  模块职责：显式发送资源引用；草稿和发布状态始终由接收产品负责。             │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict

from cyrene_reactor_product.domain import EndpointState, SendToExchangeRequest
from cyrene_reactor_product.errors import ReactorProductError
from cyrene_reactor_product.service import ReactorService, serving_artifact


class ExchangeReceiverConfiguration(BaseModel):
    """Operator-admitted receiver and existing provider bindings. | 接收权限配置。"""

    model_config = ConfigDict(extra="forbid")
    receiver_id: str
    control_url: str
    credential_file: Path
    allowed_binding_ids: frozenset[str]


def admitted_origin(value: str) -> str:
    """Require an explicit TLS origin or protected loopback tunnel. | 检查接收地址。"""
    origin = value.rstrip("/")
    parsed = urlsplit(origin)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise ValueError("HANDOFF_ORIGIN_INVALID")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        raise ValueError("HANDOFF_TLS_REQUIRED")
    if not parsed.hostname:
        raise ValueError("HANDOFF_ORIGIN_INVALID")
    return origin


class ExchangeHandoff:
    """Reuse Exchange resources and idempotency without owning route state. | 接收适配。"""

    def __init__(self, configuration: ExchangeReceiverConfiguration, source_origin: str) -> None:
        self.configuration = configuration
        self.origin = admitted_origin(configuration.control_url)
        self.source_origin = admitted_origin(source_origin)
        self.token = configuration.credential_file.read_text().strip()
        if len(self.token) < 32 or configuration.credential_file.stat().st_mode & 0o077:
            raise ValueError("EXCHANGE_CREDENTIAL_INVALID")

    def send(
        self,
        service: ReactorService,
        endpoint_id: UUID,
        command: SendToExchangeRequest,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Create an inspectable receiver draft; never confirm it. | 只创建可检查的草稿。"""
        if command.target_binding_id not in self.configuration.allowed_binding_ids:
            self._reject("RECEIVER_PERMISSION_DENIED", "Select an admitted provider binding.", 403)
        endpoint = service.get_endpoint(endpoint_id)
        if endpoint.resource_version != command.resource_version:
            self._reject("SOURCE_VERSION_CONFLICT", "Refresh the Endpoint before sending.", 409)
        if endpoint.state != EndpointState.READY or not endpoint.model:
            self._reject("SOURCE_NOT_READY", "The Endpoint has no verified model service.", 409)
        deployment = service.store.get_deployment(endpoint.deployment_id)
        assert deployment is not None
        source = {
            "product": "reactor",
            "resourceUri": self.source_origin + f"/api/v1/endpoints/{endpoint.id}",
            "resourceVersion": endpoint.resource_version,
            "artifactDigest": serving_artifact(deployment).digest,
        }
        if deployment.model_version is not None:
            source["modelVersionId"] = deployment.model_version["id"]
        payload = {
            "endpointId": str(command.gateway_endpoint_id),
            "modelPattern": command.model_pattern,
            "targetBindingId": command.target_binding_id,
            "targetModel": endpoint.model,
            "priority": command.priority,
            "source": source,
        }
        try:
            with httpx.Client(timeout=45, trust_env=False) as client:
                response = client.post(
                    self.origin + "/api/v1/gateway-route-drafts",
                    headers={
                        "Authorization": "Bearer " + self.token,
                        "Idempotency-Key": idempotency_key,
                    },
                    json=payload,
                )
                if response.is_error:
                    status = response.status_code
                    code = {
                        401: "RECEIVER_PERMISSION_DENIED",
                        403: "RECEIVER_PERMISSION_DENIED",
                        404: "RECEIVER_RESOURCE_NOT_FOUND",
                        409: "RECEIVER_VERSION_CONFLICT",
                        422: "RECEIVER_CONTRACT_INCOMPATIBLE",
                    }.get(status, "RECEIVER_UNAVAILABLE")
                    self._reject(
                        code,
                        "Exchange rejected the draft. Check access, resources and version.",
                        403
                        if status in {401, 403}
                        else status
                        if status in {404, 409, 422}
                        else 503,
                    )
                draft = response.json()
                resource_id = str(UUID(draft["id"]))
                if (
                    draft["state"] != "DRAFT"
                    or any(draft.get(key) != value for key, value in payload.items())
                    or not isinstance(draft["resourceVersion"], int)
                ):
                    self._reject(
                        "RECEIVER_RESPONSE_INCOMPATIBLE",
                        "The receiver did not return the requested draft. Inspect it in Exchange.",
                        409,
                    )
                return {
                    "product": "exchange",
                    "resourceUri": self.origin + "/api/v1/gateway-routes/" + resource_id,
                    "route": draft,
                }
        except httpx.HTTPError as exc:
            raise ReactorProductError(
                code="REACTOR_RECEIVER_UNREACHABLE",
                title="Exchange unreachable",
                detail="Restore receiver reachability and retry with the same Idempotency-Key.",
                status=503,
                retryable=True,
            ) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise ReactorProductError(
                code="REACTOR_RECEIVER_RESPONSE_INCOMPATIBLE",
                title="Exchange response incompatible",
                detail="Inspect the receiver draft before retrying; its response was incompatible.",
                status=409,
            ) from exc

    @staticmethod
    def _reject(code: str, detail: str, status: int) -> None:
        raise ReactorProductError(
            code="REACTOR_" + code,
            title="Send to Exchange failed",
            detail=detail,
            status=status,
            retryable=status == 503,
        )
