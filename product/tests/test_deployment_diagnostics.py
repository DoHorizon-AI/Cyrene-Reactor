"""Diagnostics paging tests for the Reactor Product surface.

中文：Reactor Product 接口的诊断分页测试。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.domain import (
    ArtifactRef,
    CreateModelImportRequest,
    EngineHandle,
    EngineObservation,
    ModelImportResult,
    ModelImportValidation,
    NodeRef,
)
from cyrene_reactor_product.store import ReactorStore


class _DiagnosticsPort:
    """Test double that answers the diagnostics route the way the plugin does.

        中文：按 Plugin 行为响应诊断路由的测试替身。"""

    def __init__(self) -> None:
        self.pages: dict[str, dict[str, Any]] = {}
        self.calls: list[int] = []

    def import_model(self, command: CreateModelImportRequest) -> ModelImportResult:
        del command
        return ModelImportResult(
            model_artifact=_model(),
            validation=ModelImportValidation(
                weights=True,
                config=True,
                tokenizer=True,
                chat_template=True,
                license="Apache-2.0",
                provenance="test",
                digest=f"sha256:{'d' * 64}",
            ),
        )

    def prepare(self, deployment_id: uuid4) -> EngineHandle:
        return EngineHandle(
            execution_ref=str(deployment_id),
            endpoint_url=f"https://plugin.test/serving/{deployment_id}/v1",
            model=f"reactor-{deployment_id}",
        )

    def start(
        self,
        deployment_id: uuid4,
        model: ArtifactRef,
        *,
        node_ref: NodeRef | None = None,
        model_version: dict[str, Any] | None = None,
    ) -> EngineHandle:
        del node_ref, model_version
        assert model.kind == "model"
        return self.prepare(deployment_id)

    def inspect(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: uuid4,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        del endpoint_url, model_digest, model_version
        assert execution_ref == str(deployment_id)
        return EngineObservation(ready=True, detail="READY")

    def stop(
        self,
        execution_ref: str,
        endpoint_url: str,
        deployment_id: uuid4,
        model_digest: str,
        *,
        model_version: dict[str, Any] | None = None,
    ) -> EngineObservation:
        del endpoint_url, model_digest, model_version
        assert execution_ref == str(deployment_id)
        return EngineObservation(ready=False, detail="KERNEL_RESOURCES_RELEASED")

    def diagnostics(
        self, execution_ref: str, *, after_sequence: int = 0, limit: int = 200
    ) -> dict[str, Any] | None:
        del limit
        self.calls.append(after_sequence)
        page = self.pages.get(execution_ref)
        if page is None or page["nextSequence"] <= after_sequence:
            return None if page is None else {**page, "items": []}
        return page


class _LegacyPort(_DiagnosticsPort):
    """A binding older than the diagnostics contract: no method at all.

        中文：早于诊断契约的绑定：完全没有对应方法。"""

    diagnostics = None  # type: ignore[assignment]


def _model() -> dict[str, Any]:
    return {
        "uri": f"artifact://sha256/{'a' * 64}",
        "digest": f"sha256:{'a' * 64}",
        "size_bytes": 0,
        "kind": "model",
    }


def _payload() -> dict[str, Any]:
    return {
        "name": "reference-serving",
        "modelArtifact": _model(),
        "servingBindingId": "local-process-serving",
    }


def _runtime_page(sequence: int, message: str, *, degraded: bool = False) -> dict[str, Any]:
    return {
        "resourceId": "",
        "items": [
            {
                "sequence": sequence,
                "timestamp": f"2026-01-01T00:00:0{sequence}Z",
                "level": "warn",
                "source": "runtime",
                "stream": "stderr",
                "message": message,
                "truncated": False,
            }
        ],
        "nextSequence": sequence,
        "terminal": False,
        "diagnosticsDegraded": degraded,
    }


def test_store_pages_diagnostics_and_tracks_the_runtime_cursor(tmp_path: Path) -> None:
    store = ReactorStore(tmp_path / "store.sqlite3")
    deployment_id = uuid4()
    store.append_deployment_diagnostics(
        deployment_id,
        [
            {"timestamp": "2026-01-01T00:00:00Z", "source": "product", "message": "queued"},
            {"timestamp": "2026-01-01T00:00:01Z", "source": "runtime", "message": "loading"},
        ],
    )
    first = store.list_deployment_diagnostics(deployment_id, after_sequence=0, limit=1)
    assert [record["sequence"] for record in first] == [1]
    assert first[0]["source"] == "product"
    rest = store.list_deployment_diagnostics(deployment_id, after_sequence=1)
    assert [record["sequence"] for record in rest] == [2]
    assert store.deployment_diagnostics_count(deployment_id) == 2

    assert store.runtime_diagnostics_cursor(deployment_id) == 0
    store.set_runtime_diagnostics_cursor(deployment_id, 7)
    assert store.runtime_diagnostics_cursor(deployment_id) == 7

    assert store.deployment_diagnostics_degraded(deployment_id) is False
    store.append_deployment_diagnostics(
        deployment_id, [{"code": "REACTOR.DIAGNOSTICS.DEGRADED", "message": "lost output"}]
    )
    assert store.deployment_diagnostics_degraded(deployment_id) is True
    store.close()


def test_deployment_diagnostics_merges_runtime_output_and_pages(tmp_path: Path) -> None:
    port = _DiagnosticsPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=port)
    with TestClient(app) as client:
        created = client.post("/api/v1/deployments", json=_payload())
        assert created.status_code == 201, created.text
        deployment_id = created.json()["id"]
        port.pages[deployment_id] = _runtime_page(1, "cuda kernel missing")

        page = client.get(f"/api/v1/deployments/{deployment_id}/diagnostics")
        assert page.status_code == 200, page.text
        body = page.json()
        assert body["resourceId"] == deployment_id
        sources = {item["source"] for item in body["items"]}
        assert "product" in sources
        assert "runtime" in sources
        assert body["terminal"] is False
        assert body["diagnosticsDegraded"] is False

        # The runtime is harvested once; polling again does not duplicate it.
        # 中文：运行时输出只收集一次；再次轮询不会重复记录。
        before = len(body["items"])
        again = client.get(f"/api/v1/deployments/{deployment_id}/diagnostics").json()
        assert len(again["items"]) == before

        tail = client.get(
            f"/api/v1/deployments/{deployment_id}/diagnostics?afterSequence={body['nextSequence']}"
        ).json()
        assert tail["items"] == []

        # New runtime output appears after the cursor advances.
        # 中文：游标前进后会显示新的运行时输出。
        port.pages[deployment_id] = _runtime_page(2, "engine ready")
        follow_up = client.get(f"/api/v1/deployments/{deployment_id}/diagnostics").json()
        assert any(item["message"] == "engine ready" for item in follow_up["items"])

        assert (
            client.get(f"/api/v1/deployments/{deployment_id}/diagnostics?limit=5000").status_code
            == 422
        )
    app.state.reactor_store.close()


def test_runtime_degradation_is_published(tmp_path: Path) -> None:
    port = _DiagnosticsPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=port)
    with TestClient(app) as client:
        deployment_id = client.post("/api/v1/deployments", json=_payload()).json()["id"]
        port.pages[deployment_id] = _runtime_page(1, "line", degraded=True)
        body = client.get(f"/api/v1/deployments/{deployment_id}/diagnostics").json()
        assert body["diagnosticsDegraded"] is True
        assert any(item.get("code") == "REACTOR.DIAGNOSTICS.DEGRADED" for item in body["items"])
    app.state.reactor_store.close()


def test_deployment_diagnostics_degrades_for_a_legacy_binding(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=_LegacyPort())
    with TestClient(app) as client:
        deployment_id = client.post("/api/v1/deployments", json=_payload()).json()["id"]
        page = client.get(f"/api/v1/deployments/{deployment_id}/diagnostics")
        assert page.status_code == 200
        body = page.json()
        assert body["diagnosticsDegraded"] is True
        # Product records are still returned.
        # 中文：仍会返回 Product 记录。
        assert any(item["source"] == "product" for item in body["items"])
    app.state.reactor_store.close()


def test_unknown_deployment_diagnostics_is_not_found(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=_DiagnosticsPort())
    with TestClient(app) as client:
        response = client.get(f"/api/v1/deployments/{uuid4()}/diagnostics")
        assert response.status_code == 404
        assert response.json()["code"] == "REACTOR_DEPLOYMENT_NOT_FOUND"
    app.state.reactor_store.close()
