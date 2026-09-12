"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 test_exchange_handoff.py                                        │
│  Module: reactor_product.tests                                     │
│  Role: Source versions, explicit publication intent and permissions.│
│  模块职责：验证发送草稿、版本和权限；测试端口不是模型推理证据。              │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.domain import ArtifactRef, EngineHandle, EngineObservation, NodeRef
from cyrene_reactor_product.exchange_handoff import ExchangeHandoff, ExchangeReceiverConfiguration


class UnitEngine:
    """No GPU or model process: exercises Product state only. | 仅验证产品状态。"""

    def prepare(self, deployment_id: UUID) -> EngineHandle:
        return EngineHandle(
            execution_ref=str(deployment_id),
            endpoint_url="https://node.example/serving/" + str(deployment_id) + "/v1",
            model="unit-" + str(deployment_id),
        )

    def start(
        self, deployment_id: UUID, model: ArtifactRef, *, node_ref: NodeRef | None = None
    ) -> EngineHandle:
        return self.prepare(deployment_id)

    def inspect(
        self, execution_ref: str, endpoint_url: str, deployment_id: UUID, model_digest: str
    ) -> EngineObservation:
        return EngineObservation(ready=True, detail="unit observation")

    def stop(
        self, execution_ref: str, endpoint_url: str, deployment_id: UUID, model_digest: str
    ) -> EngineObservation:
        return EngineObservation(ready=False, detail="unit cleanup")


def test_send_is_explicit_and_restart_invalidates_previously_inspected_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    credential = tmp_path / "credential"
    credential.write_text("unit-control-token-" + "x" * 32)
    credential.chmod(0o600)
    receiver = ExchangeHandoff(
        ExchangeReceiverConfiguration(
            receiver_id="exchange",
            control_url="https://exchange.example",
            credential_file=credential,
            allowed_binding_ids=frozenset({"existing-provider"}),
        ),
        "https://reactor.example",
    )
    app = create_app(
        database_path=tmp_path / "reactor.sqlite3",
        engines={"admitted": UnitEngine()},
        exchange_receivers={"exchange": receiver},
    )
    seen: list[dict[str, object]] = []

    def receive(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/gateway-route-drafts"
        assert request.headers["Idempotency-Key"] == "one-send"
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(
            201,
            json={
                **body,
                "id": "11111111-1111-4111-8111-111111111111",
                "state": "DRAFT",
                "resourceVersion": 1,
            },
        )

    original_client = httpx.Client
    with TestClient(app) as client:
        monkeypatch.setattr(
            "cyrene_reactor_product.exchange_handoff.httpx.Client",
            lambda **kwargs: original_client(transport=httpx.MockTransport(receive), **kwargs),
        )
        deployment = client.post(
            "/api/v1/deployments",
            json={
                "name": "unit deployment",
                "modelArtifact": {
                    "uri": "artifact://sha256/" + "a" * 64,
                    "digest": "sha256:" + "a" * 64,
                    "size_bytes": 4,
                    "kind": "model",
                },
                "servingBindingId": "admitted",
                "nodeRef": {"nodeId": "unit-node", "nodeEpoch": 1},
            },
        ).json()
        assert deployment["observedState"] == "READY"
        assert seen == []
        endpoint_path = "/api/v1/endpoints/" + deployment["endpointId"]
        endpoint = client.get(endpoint_path).json()
        command = {
            "resourceVersion": endpoint["resourceVersion"],
            "receiverId": "exchange",
            "gatewayEndpointId": "22222222-2222-4222-8222-222222222222",
            "targetBindingId": "existing-provider",
            "modelPattern": "my-chat",
        }
        send_path = endpoint_path + "/actions/send-to-exchange"
        assert client.post(send_path, json=command).status_code == 422
        response = client.post(send_path, json=command, headers={"Idempotency-Key": "one-send"})
        assert response.status_code == 201
        assert response.json()["route"]["state"] == "DRAFT"
        assert seen[0]["targetModel"] == endpoint["model"]
        assert seen[0]["source"] == {
            "product": "reactor",
            "resourceUri": "https://reactor.example" + endpoint_path,
            "resourceVersion": endpoint["resourceVersion"],
            "artifactDigest": "sha256:" + "a" * 64,
        }
        denied = client.post(
            send_path,
            json={**command, "targetBindingId": "not-admitted"},
            headers={"Idempotency-Key": "one-send"},
        )
        assert denied.status_code == 403
        deployment_path = "/api/v1/deployments/" + deployment["id"]
        stopped = client.post(deployment_path + "/actions/stop").json()
        restarted = client.post(
            deployment_path + "/actions/restart",
            json={
                "resourceVersion": stopped["resourceVersion"],
                "nodeRef": {"nodeId": "unit-node", "nodeEpoch": 2},
            },
        )
        assert restarted.status_code == 200
        current = client.get(endpoint_path).json()
        assert current["id"] == endpoint["id"]
        assert current["createdAt"] == endpoint["createdAt"]
        assert current["resourceVersion"] > endpoint["resourceVersion"]
        stale = client.post(send_path, json=command, headers={"Idempotency-Key": "one-send"})
        assert stale.status_code == 409
        assert len(seen) == 1
