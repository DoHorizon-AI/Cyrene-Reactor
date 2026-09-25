"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 test_product_mvp.py                                             │
│  Module: tests.test_product_mvp                                     │
│  Role: Product lifecycle, failure, restart, and stop acceptance.     │
│                                                                     │
│  模块职责：验证真实进程、HTTP、失败、重启协调与停止生命周期。                 │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker, validate
from openapi_spec_validator.readers import read_from_filename
from referencing import Registry, Resource

from cyrene_reactor_product import create_app
from cyrene_reactor_product.domain import (
    ArtifactRef,
    CreateModelImportRequest,
    EngineHandle,
    EngineObservation,
    ModelImportResult,
    ModelImportValidation,
    NodeRef,
)
from cyrene_reactor_product.errors import ServingEngineFailure


class _TestServingExecutionPort:
    """State-sharing test double for Product lifecycle orchestration only.

        中文：仅用于 Product 生命周期协调的共享状态测试替身。"""

    def __init__(self, executions: dict[str, dict[str, Any]] | None = None) -> None:
        self.executions = executions if executions is not None else {}
        self.imports: dict[str, CreateModelImportRequest] = {}

    def import_model(self, command: CreateModelImportRequest) -> ModelImportResult:
        source = command.source.repository or command.source.path or ""
        self.imports[source] = command
        if command.source.repository == "missing/model":
            raise ServingEngineFailure(
                "SERVING_MODEL_SOURCE_UNAVAILABLE: the pinned source cannot be read",
                status=503,
                retryable=True,
            )
        return ModelImportResult(
            model_artifact=ArtifactRef(
                uri=f"artifact://sha256/{'c' * 64}",
                digest=f"sha256:{'c' * 64}",
                size_bytes=1,
                kind="model",
            ),
            validation=ModelImportValidation(
                weights=True,
                config=True,
                tokenizer=True,
                chat_template=True,
                license="Apache-2.0",
                provenance=source,
                digest=f"sha256:{'d' * 64}",
            ),
        )

    def prepare(self, deployment_id: UUID) -> EngineHandle:
        return EngineHandle(
            execution_ref=str(deployment_id),
            endpoint_url=f"https://plugin.test/serving/{deployment_id}/v1",
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
        del node_ref, model_version
        if model.kind != "model":
            raise ServingEngineFailure("The test port requires a model ArtifactRef.")
        handle = self.prepare(deployment_id)
        self.executions[str(deployment_id)] = {
            "active": True,
            "model_digest": model.digest,
            "endpoint_url": handle.endpoint_url,
        }
        return handle

    def inspect(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        del model_version
        record = self.executions.get(str(deployment_id))
        ready = bool(
            record
            and record["active"]
            and execution_ref == str(deployment_id)
            and endpoint_url == record["endpoint_url"]
            and model_digest == record["model_digest"]
        )
        return EngineObservation(ready=ready, detail="identity verified" if ready else "missing")

    def stop(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: UUID,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        observation = self.inspect(
            execution_ref,
            endpoint_url,
            deployment_id,
            model_digest,
            model_version=model_version,
        )
        if observation.ready:
            self.executions[str(deployment_id)]["active"] = False
        return EngineObservation(ready=False, detail="released")


def _model(kind: str = "model") -> dict[str, Any]:
    return {
        "uri": f"artifact://sha256/{'a' * 64}",
        "digest": f"sha256:{'a' * 64}",
        "size_bytes": 0,
        "kind": kind,
    }


def test_runtime_paths_match_frozen_openapi(tmp_path: Path) -> None:
    engine = _TestServingExecutionPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=engine)
    contract, _ = read_from_filename(
        str(Path(__file__).parents[2] / "contracts/product/v1/openapi.yaml")
    )
    assert set(app.openapi()["paths"]) == set(contract["paths"])
    app.state.reactor_store.close()


def test_lifecycle_restart_reconcile_and_stop(tmp_path: Path) -> None:
    database = tmp_path / "reactor.sqlite3"
    executions: dict[str, dict[str, Any]] = {}
    engine_before_restart = _TestServingExecutionPort(executions)
    app = create_app(database_path=database, engine=engine_before_restart)
    restarted_engine = _TestServingExecutionPort(executions)
    restarted = None
    deployment: dict[str, Any] = {}
    endpoint: dict[str, Any] = {}
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deployments",
                headers={"Idempotency-Key": "deployment-demo"},
                json={
                    "name": "reference-serving",
                    "modelArtifact": _model(),
                    "servingBindingId": "local-process-serving",
                },
            )
            assert response.status_code == 201
            deployment = response.json()
            assert deployment["observedState"] == "READY"
            assert deployment["servingCapabilityType"] == "execution.engine.v1"
            assert "engineExecutionRef" not in deployment
            endpoint = client.get(f"/api/v1/endpoints/{deployment['endpointId']}").json()
            assert endpoint["deploymentId"] == deployment["id"]
            assert endpoint["state"] == "READY"
            assert endpoint["url"] == executions[deployment["id"]]["endpoint_url"]
        app.state.reactor_store.close()

        restarted = create_app(database_path=database, engine=restarted_engine)
        with TestClient(restarted) as client:
            reconciled = client.get(f"/api/v1/deployments/{deployment['id']}")
            assert reconciled.status_code == 200
            assert reconciled.json()["observedState"] == "READY"
            stopped = client.post(f"/api/v1/deployments/{deployment['id']}/actions/stop")
            assert stopped.status_code == 200
            assert stopped.json()["desiredState"] == "STOPPED"
            assert stopped.json()["observedState"] == "STOPPED"
            retired = client.get(f"/api/v1/endpoints/{endpoint['id']}").json()
            assert retired["state"] == "RETIRED"

        assert executions[deployment["id"]]["active"] is False

        contract_root = Path(__file__).parents[2] / "contracts/product/v1"
        deployment_schema = json.loads((contract_root / "deployment.schema.json").read_text())
        artifact_schema = json.loads(
            (contract_root / "generated/platform/artifact-ref.schema.json").read_text()
        )
        registry = Registry().with_resource(
            artifact_schema["$id"], Resource.from_contents(artifact_schema)
        )
        Draft202012Validator(
            deployment_schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).validate(deployment)
        endpoint_schema = json.loads((contract_root / "endpoint.schema.json").read_text())
        validate(instance=endpoint, schema=endpoint_schema, format_checker=FormatChecker())
    finally:
        if restarted is not None:
            restarted.state.reactor_store.close()


def test_unsupported_model_persists_failed_deployment(tmp_path: Path) -> None:
    engine = _TestServingExecutionPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=engine)
    try:
        with TestClient(app) as client:
            command = {
                "name": "unsupported",
                "modelArtifact": _model("dataset"),
                "servingBindingId": "local-process-serving",
            }
            response = client.post(
                "/api/v1/deployments",
                headers={"Idempotency-Key": "unsupported-deployment"},
                json=command,
            )
            assert response.status_code == 422
            assert response.headers["content-type"].startswith("application/problem+json")
            problem = response.json()
            assert problem["code"] == "REACTOR_SERVING_START_FAILED"
            persisted = client.get(problem["resourceRef"])
            assert persisted.status_code == 200
            assert persisted.json()["observedState"] == "FAILED"
            assert persisted.json()["failure"]["code"] == "REACTOR_SERVING_START_FAILED"

            replay = client.post(
                "/api/v1/deployments",
                headers={"Idempotency-Key": "unsupported-deployment"},
                json=command,
            )
            assert replay.status_code == 201
            assert replay.json() == persisted.json()
    finally:
        app.state.reactor_store.close()


def test_legacy_execution_reference_is_migrated_out_of_product_json(tmp_path: Path) -> None:
    database = tmp_path / "reactor.sqlite3"
    deployment_id = "11111111-1111-4111-8111-111111111111"
    legacy = {
        "id": deployment_id,
        "name": "legacy",
        "modelArtifact": _model(),
        "desiredState": "ACTIVE",
        "observedState": "READY",
        "servingBindingId": "local-process-serving",
        "servingCapabilityType": "execution.engine.v1",
        "engineExecutionRef": "process:1234",
        "endpointId": "22222222-2222-4222-8222-222222222222",
        "createdAt": "2026-09-01T00:00:00Z",
        "updatedAt": "2026-09-01T00:00:00Z",
        "resourceVersion": 2,
    }
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE deployments (id TEXT PRIMARY KEY, document TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO deployments(id, document) VALUES (?, ?)",
            (deployment_id, json.dumps(legacy)),
        )

    engine = _TestServingExecutionPort()
    app = create_app(database_path=database, engine=engine)
    try:
        with TestClient(app) as client:
            deployment = client.get(f"/api/v1/deployments/{deployment_id}").json()
        assert "engineExecutionRef" not in deployment
        assert app.state.reactor_store.get_execution_ref(UUID(deployment_id)) == "process:1234"
    finally:
        app.state.reactor_store.close()


def test_deployment_events_record_phase_transitions(tmp_path: Path) -> None:
    engine = _TestServingExecutionPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=engine)
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/deployments",
                json={
                    "name": "phase-test",
                    "modelArtifact": _model(),
                    "servingBindingId": "local-process-serving",
                },
            )
            assert created.status_code == 201, created.text
            deployment_id = created.json()["id"]

            res = client.get(f"/api/v1/deployments/{deployment_id}/events")
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["deploymentId"] == deployment_id
            events = data["events"]
            # At least 3 phase transitions recorded
            # 中文：至少记录 3 次阶段转换。
            assert len(events) >= 3
            phases = [e["phase"] for e in events]
            assert "QUEUED" in phases
            assert "LOADING" in phases
            assert "PROBING" in phases
            assert "READY" in phases
            assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))

            # Stop deployment and check STOPPING and RELEASED events
            # 中文：停止 Deployment，并检查 STOPPING 与 RELEASED 事件。
            client.post(f"/api/v1/deployments/{deployment_id}/actions/stop")
            res_after_stop = client.get(f"/api/v1/deployments/{deployment_id}/events")
            assert res_after_stop.status_code == 200
            events_stop = res_after_stop.json()["events"]
            assert len(events_stop) >= 5
            phases_stop = [e["phase"] for e in events_stop]
            assert "STOPPING" in phases_stop
            assert "RELEASED" in phases_stop

            # 404 for non-existent deployment
            # 中文：不存在的 Deployment 返回 404。
            missing = client.get(f"/api/v1/deployments/{uuid4()}/events")
            assert missing.status_code == 404
            assert missing.json()["code"] == "REACTOR_DEPLOYMENT_NOT_FOUND"
    finally:
        app.state.reactor_store.close()
