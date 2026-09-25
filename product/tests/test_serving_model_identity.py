"""Focused serving model-registry identity tests. | 服务模型注册表身份定向测试。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.remote_engine import (
    RemoteServingExecutionPort,
    ServingBindingConfiguration,
)


def _artifact() -> dict[str, Any]:
    """Return the minimal model artifact accepted by the Product contract.

        中文：返回 Product 契约接受的最小模型 Artifact。"""

    digest = "sha256:" + "a" * 64
    return {
        "uri": "artifact://sha256/" + "a" * 64,
        "digest": digest,
        "size_bytes": 1,
        "kind": "model",
    }


def test_model_registry_mismatch_fails_the_started_deployment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Require the intended model ID in the serving endpoint and persist FAILED.

        中文：要求服务端点中的模型 ID 与预期一致，并持久化 FAILED 状态。"""

    credential = tmp_path / "credential"
    credential.write_text("serving-test-token-" + "x" * 32)
    credential.chmod(0o600)
    engine = RemoteServingExecutionPort(
        ServingBindingConfiguration(
            binding_id="remote",
            control_url="https://node.example",
            credential_file=credential,
        )
    )
    model = _artifact()
    model_probe_paths: list[str] = []
    stop_paths: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stop"):
            stop_paths.append(request.url.path)
            assert request.headers["Authorization"].startswith("Bearer serving-test-token-")
            return httpx.Response(200, json={"released": True})
        if request.url.path.startswith("/executions/"):
            deployment_id = UUID(request.url.path.rsplit("/", 1)[-1])
            result = {
                "ready": True,
                "detail": "ready",
                "endpointUrl": f"https://node.example/serving/{deployment_id}/v1",
                "servedModel": f"reactor-{deployment_id}",
                "modelArtifact": model,
            }
            return httpx.Response(200, json=result)
        if request.url.path.endswith("/models"):
            model_probe_paths.append(request.url.path)
            assert request.headers["Authorization"].startswith("Bearer serving-test-token-")
            return httpx.Response(
                200,
                json={"object": "list", "data": [{"id": "wrong-served-model"}]},
            )
        if request.url.path.endswith("/chat/completions"):
            body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "model": body["model"],
                    "choices": [{"message": {"content": "ready"}}],
                },
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    original_client = httpx.Client
    monkeypatch.setattr(
        "cyrene_reactor_product.remote_engine.httpx.Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs),
    )
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engines={"remote": engine})
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deployments",
                json={
                    "name": "identity-check",
                    "modelArtifact": model,
                    "servingBindingId": "remote",
                    "nodeRef": {"nodeId": "node-1", "nodeEpoch": 1},
                },
            )
            assert response.status_code == 409, response.text
            assert response.json()["code"] == "REACTOR_SERVING_START_FAILED"
            assert "MODEL_IDENTITY_MISMATCH" in response.json()["detail"]

            failed = client.get(response.json()["resourceRef"])
            assert failed.status_code == 200
            assert failed.json()["observedState"] == "FAILED"
            assert "MODEL_IDENTITY_MISMATCH" in failed.json()["failure"]["message"]
            assert model_probe_paths == [f"/serving/{failed.json()['id']}/v1/models"]
            assert stop_paths == [f"/executions/{failed.json()['id']}/stop"]
    finally:
        app.state.reactor_store.close()
