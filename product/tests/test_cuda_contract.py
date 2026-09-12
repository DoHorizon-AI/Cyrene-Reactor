"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 test_cuda_contract.py                                           │
│  Module: reactor_product.tests                                     │
│  Role: Artifact identity and uncertain-start recovery regressions.│
│  模块职责：验证制品身份与启动结果不确定时的恢复，不作为模型推理证据。         │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from cy_artifacts import LocalArtifactProvider
from cyrene_yield_contracts import YieldArtifactKind
from fastapi.testclient import TestClient

from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.domain import ArtifactRef, EngineHandle, EngineObservation, NodeRef
from cyrene_reactor_product.errors import ServingEngineFailure
from cyrene_reactor_product.remote_engine import (
    RemoteServingExecutionPort,
    ServingBindingConfiguration,
)


def package(root: Path) -> Path:
    """Create an opaque Product test artifact without interpreting model contents."""
    root.mkdir()
    (root / "artifact.bin").write_bytes(b"opaque-model-package")
    return root


class UncertainEngine:
    """A unit-test port that fails after receiving the launch command. | 启动未知结果测试。"""

    def __init__(self) -> None:
        self.stopped: list[str] = []

    def prepare(self, deployment_id: UUID) -> EngineHandle:
        return EngineHandle(
            execution_ref=str(deployment_id), endpoint_url="https://node.example/v1"
        )

    def start(
        self, deployment_id: UUID, model: ArtifactRef, *, node_ref: NodeRef | None = None
    ) -> EngineHandle:
        raise ServingEngineFailure("CONTROL_CONNECTION_LOST")

    def inspect(
        self, execution_ref: str, endpoint_url: str, deployment_id: UUID, model_digest: str
    ) -> EngineObservation:
        return EngineObservation(ready=False, detail="unreachable")

    def stop(
        self, execution_ref: str, endpoint_url: str, deployment_id: UUID, model_digest: str
    ) -> EngineObservation:
        self.stopped.append(execution_ref)
        return EngineObservation(ready=False, detail="release confirmed by test port")


def test_uncertain_start_preserves_identity_for_stop_and_idempotent_replay(tmp_path: Path) -> None:
    engine = UncertainEngine()
    app = create_app(database_path=tmp_path / "product.sqlite3", engines={"selected": engine})
    model = package(tmp_path / "model")
    artifact = LocalArtifactProvider(tmp_path / "cas").publish_portable_directory(
        model, kind=YieldArtifactKind.MODEL
    )
    with TestClient(app) as client:
        payload = {
            "name": "uncertain",
            "modelArtifact": artifact.to_dict(),
            "servingBindingId": "selected",
            "nodeRef": {"nodeId": "selected-node", "nodeEpoch": 1},
        }
        response = client.post(
            "/api/v1/deployments", json=payload, headers={"Idempotency-Key": "one-attempt"}
        )
        assert response.status_code == 422
        reference = response.json()["resourceRef"]
        resource = client.get(reference).json()
        assert resource["observedState"] == "FAILED"
        assert "endpointId" in resource
        assert "executionRef" not in json.dumps(resource)
        replay = client.post(
            "/api/v1/deployments", json=payload, headers={"Idempotency-Key": "one-attempt"}
        )
        assert replay.json()["id"] == resource["id"]
        stopped = client.post(reference + "/actions/stop")
        assert stopped.status_code == 200
        assert stopped.json()["observedState"] == "STOPPED"
        assert engine.stopped == [resource["id"]]
        payload["servingBindingId"] = "not-authorized"
        assert client.post("/api/v1/deployments", json=payload).status_code == 403


@pytest.mark.parametrize("failure", ["permission", "connection", "invalid-release"])
def test_remote_failures_keep_permission_and_cleanup_evidence_distinct(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    token = tmp_path / "credential"
    token.write_text("unit-binding-token-" + "x" * 32)
    token.chmod(0o600)
    engine = RemoteServingExecutionPort(
        ServingBindingConfiguration(
            binding_id="unit",
            control_url="https://node.example",
            credential_file=token,
        )
    )

    def respond(request: httpx.Request) -> httpx.Response:
        if failure == "permission":
            return httpx.Response(403, json={"detail": "permission denied"})
        if failure == "connection":
            raise httpx.ConnectError("controlled unreachable binding", request=request)
        return httpx.Response(200, json={"released": "true"})

    original_client = httpx.Client
    monkeypatch.setattr(
        "cyrene_reactor_product.remote_engine.httpx.Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    if failure == "invalid-release":
        identity = UUID("11111111-1111-4111-8111-111111111111")
        with pytest.raises(ServingEngineFailure, match="KERNEL_CLEANUP_INCOMPLETE"):
            engine.stop(str(identity), "https://node.example/v1", identity, "sha256:" + "a" * 64)
    else:
        with pytest.raises(ServingEngineFailure) as caught:
            engine.request("GET", "/node")
        assert caught.value.status == (403 if failure == "permission" else 503)
        assert caught.value.retryable == (failure == "connection")
