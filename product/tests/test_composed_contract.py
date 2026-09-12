"""Focused composed Deployment contract tests. | composed 部署契约定向测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest
from cyrene_yield_contracts import ModelVersion
from fastapi.testclient import TestClient

from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.domain import ArtifactRef, EngineHandle, EngineObservation, NodeRef
from cyrene_reactor_product.remote_engine import (
    RemoteServingExecutionPort,
    ServingBindingConfiguration,
)


def _artifact(fill: str) -> dict[str, Any]:
    digest = "sha256:" + fill * 64
    return {
        "uri": "artifact://sha256/" + fill * 64,
        "digest": digest,
        "size_bytes": 10,
        "kind": "model",
        "manifest_digest": digest,
    }


class _ComposedEngine:
    def __init__(self, *, report_identity: bool = True) -> None:
        self.seen: dict[str, Any] = {}
        self.report_identity = report_identity
        self.stop_calls = 0

    def prepare(self, deployment_id: UUID) -> EngineHandle:
        return EngineHandle(
            execution_ref=str(deployment_id),
            endpoint_url=f"https://node.example/serving/{deployment_id}/v1",
            model=f"reactor-{deployment_id}",
        )

    def start(
        self,
        deployment_id: UUID,
        model: ArtifactRef,
        *,
        node_ref: NodeRef | None = None,
        model_version: dict[str, Any] | None = None,
    ) -> EngineHandle:
        assert model_version is not None
        self.seen["start"] = (model, model_version, node_ref)
        return EngineHandle(
            execution_ref=str(deployment_id),
            endpoint_url=f"https://node.example/serving/{deployment_id}/v1",
            model=f"reactor-{deployment_id}",
            model_version_id=model_version["id"] if self.report_identity else None,
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
        assert model_version is not None
        assert model_digest == model_version["id"]
        return EngineObservation(ready=True, detail="composed identity verified")

    def stop(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        assert model_version is not None
        assert model_digest == model_version["id"]
        self.stop_calls += 1
        return EngineObservation(ready=False, detail="released")


def test_composed_request_persists_canonical_identity(tmp_path: Path) -> None:
    engine = _ComposedEngine()
    app = create_app(
        database_path=tmp_path / "reactor.sqlite3",
        engines={"composed": engine},
    )
    model_version = ModelVersion.create(
        {
            "schemaVersion": "1",
            "composition": "BASE_PLUS_LORA",
            "baseModel": {
                "artifact": _artifact("a"),
                "source": {
                    "repository": "Qwen/Qwen2.5-1.5B-Instruct",
                    "revision": "b" * 40,
                },
            },
            "adapterArtifact": _artifact("c"),
            "tokenizer": {"mode": "INHERIT"},
            "chatTemplate": {"mode": "INHERIT"},
            "lineage": {},
        }
    )
    payload = {
        "name": "composed-serving",
        "composition": "BASE_PLUS_LORA",
        "modelVersion": model_version.to_dict(),
        "servingBindingId": "composed",
        "nodeRef": {"nodeId": "node-1", "nodeEpoch": 1},
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/deployments", json=payload)
        assert response.status_code == 201, response.text
        deployment = response.json()
    assert deployment["composition"] == "BASE_PLUS_LORA"
    assert deployment["modelVersion"]["id"].startswith("model-version://sha256/")
    assert deployment["modelArtifact"]["digest"] == "sha256:" + "a" * 64
    assert engine.seen["start"][1]["id"] == deployment["modelVersion"]["id"]

    with TestClient(app) as client:
        stopped = client.post(f"/api/v1/deployments/{deployment['id']}/actions/stop")
        assert stopped.status_code == 200, stopped.text
        restarted = client.post(
            f"/api/v1/deployments/{deployment['id']}/actions/restart",
            json={
                "resourceVersion": stopped.json()["resourceVersion"],
                "nodeRef": {"nodeId": "node-2", "nodeEpoch": 2},
            },
        )
        assert restarted.status_code == 200, restarted.text
        assert restarted.json()["modelVersion"]["id"] == deployment["modelVersion"]["id"]
    assert engine.seen["start"][1]["id"] == deployment["modelVersion"]["id"]


def test_composed_identity_mismatch_stops_execution_and_fails_closed(tmp_path: Path) -> None:
    engine = _ComposedEngine(report_identity=False)
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engines={"composed": engine})
    model_version = ModelVersion.create(
        {
            "schemaVersion": "1",
            "composition": "BASE_PLUS_LORA",
            "baseModel": {
                "artifact": _artifact("a"),
                "source": {
                    "repository": "Qwen/Qwen2.5-1.5B-Instruct",
                    "revision": "b" * 40,
                },
            },
            "adapterArtifact": _artifact("c"),
            "tokenizer": {"mode": "INHERIT"},
            "chatTemplate": {"mode": "INHERIT"},
            "lineage": {},
        }
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/deployments",
            json={
                "name": "identity-mismatch",
                "composition": "BASE_PLUS_LORA",
                "modelVersion": model_version.to_dict(),
                "servingBindingId": "composed",
                "nodeRef": {"nodeId": "node-1", "nodeEpoch": 1},
            },
        )
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "REACTOR_SERVING_START_FAILED"
    assert engine.stop_calls == 1


def test_imported_draft_requires_explicit_deploy_and_preserves_retry_identity(
    tmp_path: Path,
) -> None:
    engine = _ComposedEngine()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engines={"composed": engine})
    version = ModelVersion.create(
        {
            "schemaVersion": "1",
            "composition": "BASE_PLUS_LORA",
            "baseModel": {
                "artifact": _artifact("a"),
                "source": {"repository": "example/text-base", "revision": "b" * 40},
            },
            "adapterArtifact": _artifact("c"),
            "tokenizer": {"mode": "INHERIT"},
            "chatTemplate": {"mode": "INHERIT"},
            "lineage": {},
        }
    ).to_dict()
    source_id = "11111111-1111-4111-8111-111111111111"
    payload = {
        "sourceRef": {
            "uri": f"cyrene://yield/training-results/{source_id}",
            "id": source_id,
            "resourceVersion": 1,
        },
        "modelVersion": version,
    }
    with TestClient(app) as client:
        imported = client.post(
            "/api/v1/deployment-drafts",
            json=payload,
            headers={"Idempotency-Key": "selected-result"},
        )
        assert imported.status_code == 201, imported.text
        draft = imported.json()
        assert draft["state"] == "DRAFT" and "deploymentRef" not in draft
        assert engine.seen == {} and client.get("/api/v1/deployments").json() == []
        replay = client.post(
            "/api/v1/deployment-drafts",
            json=payload,
            headers={"Idempotency-Key": "selected-result"},
        )
        assert replay.json() == draft
        payload["sourceRef"]["resourceVersion"] = 2
        conflict = client.post(
            "/api/v1/deployment-drafts",
            json=payload,
            headers={"Idempotency-Key": "selected-result"},
        )
        assert conflict.status_code == 409
        request = {
            "name": "explicit deployment",
            "servingBindingId": "composed",
            "nodeRef": {"nodeId": "node-1", "nodeEpoch": 1},
        }
        path = f"/api/v1/deployment-drafts/{draft['id']}"
        deployed = client.post(path + "/actions/deploy", json=request)
        assert deployed.status_code == 201, deployed.text
        assert deployed.json()["modelVersion"]["id"] == version["id"]
        repeated = client.post(path + "/actions/deploy", json=request)
        assert repeated.json()["id"] == deployed.json()["id"]
        assert len(client.get("/api/v1/deployments").json()) == 1
        saved = client.get(path).json()
        assert saved["state"] == "STARTED"
        assert saved["deploymentRef"]["id"] == deployed.json()["id"]


def test_composed_model_export_is_explicitly_unsupported(tmp_path: Path) -> None:
    engine = _ComposedEngine()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engines={"composed": engine})
    model_version = ModelVersion.create(
        {
            "schemaVersion": "1",
            "composition": "BASE_PLUS_LORA",
            "baseModel": {
                "artifact": _artifact("a"),
                "source": {
                    "repository": "Qwen/Qwen2.5-1.5B-Instruct",
                    "revision": "b" * 40,
                },
            },
            "adapterArtifact": _artifact("c"),
            "tokenizer": {"mode": "INHERIT"},
            "chatTemplate": {"mode": "INHERIT"},
            "lineage": {},
        }
    )
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/deployments",
            json={
                "name": "composed-export",
                "composition": "BASE_PLUS_LORA",
                "modelVersion": model_version.to_dict(),
                "servingBindingId": "composed",
                "nodeRef": {"nodeId": "node-1", "nodeEpoch": 1},
            },
        )
        assert created.status_code == 201, created.text
        exported = client.get(f"/api/v1/deployments/{created.json()['id']}/model-export")
    assert exported.status_code == 409
    assert exported.json()["code"] == "COMPOSED_MODEL_EXPORT_UNSUPPORTED"


def test_remote_port_sends_and_reads_composed_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    credential = tmp_path / "credential"
    credential.write_text("remote-test-token-" + "x" * 32)
    credential.chmod(0o600)
    engine = RemoteServingExecutionPort(
        ServingBindingConfiguration(
            binding_id="composed",
            control_url="https://node.example",
            credential_file=credential,
        )
    )
    deployment_id = UUID("11111111-1111-4111-8111-111111111111")
    version = ModelVersion.create(
        {
            "schemaVersion": "1",
            "composition": "BASE_PLUS_LORA",
            "baseModel": {
                "artifact": _artifact("a"),
                "source": {
                    "repository": "Qwen/Qwen2.5-1.5B-Instruct",
                    "revision": "b" * 40,
                },
            },
            "adapterArtifact": _artifact("c"),
            "tokenizer": {"mode": "INHERIT"},
            "chatTemplate": {"mode": "INHERIT"},
            "lineage": {},
        }
    ).to_dict()
    seen: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/executions/{deployment_id}" and request.method == "POST":
            body = json.loads(request.content)
            seen.append(body)
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "detail": "ready",
                    "endpointUrl": f"https://node.example/serving/{deployment_id}/v1",
                    "servedModel": f"reactor-{deployment_id}",
                    "modelArtifact": _artifact("a"),
                    "modelVersion": version,
                },
            )
        if request.url.path == f"/executions/{deployment_id}" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "detail": "ready",
                    "endpointUrl": f"https://node.example/serving/{deployment_id}/v1",
                    "servedModel": f"reactor-{deployment_id}",
                    "modelArtifact": _artifact("a"),
                    "modelVersion": version,
                },
            )
        if request.url.path.endswith("/chat/completions"):
            return httpx.Response(
                200,
                json={
                    "model": f"reactor-{deployment_id}",
                    "choices": [{"message": {"content": "ready"}}],
                },
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    original_client = httpx.Client
    monkeypatch.setattr(
        "cyrene_reactor_product.remote_engine.httpx.Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    handle = engine.start(
        deployment_id,
        ArtifactRef.model_validate(_artifact("a")),
        node_ref=NodeRef(node_id="node-1", node_epoch=1),
        model_version=version,
    )
    assert seen[0]["modelVersion"]["id"] == version["id"]
    assert handle.model_version_id == version["id"]

    expected_version = version
    wrong_version = ModelVersion.create(
        {
            "schemaVersion": "1",
            "composition": "BASE_PLUS_LORA",
            "baseModel": {
                "artifact": _artifact("d"),
                "source": {
                    "repository": "Qwen/Qwen2.5-1.5B-Instruct",
                    "revision": "b" * 40,
                },
            },
            "adapterArtifact": _artifact("c"),
            "tokenizer": {"mode": "INHERIT"},
            "chatTemplate": {"mode": "INHERIT"},
            "lineage": {},
        }
    ).to_dict()
    version = wrong_version
    observation = engine.inspect(
        str(deployment_id),
        f"https://node.example/serving/{deployment_id}/v1",
        deployment_id,
        expected_version["id"],
        model_version=expected_version,
    )
    assert observation.ready is False
