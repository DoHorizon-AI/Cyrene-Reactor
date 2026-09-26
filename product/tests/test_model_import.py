"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 test_model_import.py                                            │
│  Module: tests.test_model_import                                    │
│  Role: Persisted ModelImport lifecycle, validation, and idempotency. │
│                                                                     │
│  模块职责：验证模型导入资源、校验门禁、失败持久化与幂等重放。               │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from test_product_mvp import _TestServingExecutionPort

from cyrene_reactor_product import create_app

COMMIT = "5fee7c4ed634dc66c6e318c8ac2897b8b9154536"


def _hugging_face_source() -> dict[str, object]:
    return {
        "kind": "HUGGING_FACE",
        "repository": "Qwen/Qwen2.5-1.5B-Instruct",
        "revision": COMMIT,
    }


def test_import_lifecycle_read_back_and_idempotent_replay(tmp_path: Path) -> None:
    engine = _TestServingExecutionPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=engine)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/model-imports",
                headers={"Idempotency-Key": "acceptance-model"},
                json={
                    "name": "acceptance-model",
                    "servingBindingId": "local-process-serving",
                    "source": _hugging_face_source(),
                },
            )
            assert response.status_code == 201, response.text
            model_import = response.json()
            assert model_import["state"] == "READY"
            assert model_import["modelArtifact"]["kind"] == "model"
            assert model_import["validation"]["weights"] is True
            assert model_import["validation"]["chatTemplate"] is True
            assert model_import["validation"]["trustRemoteCode"] is False
            assert model_import["validation"]["license"] == "Apache-2.0"
            assert model_import["source"]["revision"] == COMMIT

            replay = client.post(
                "/api/v1/model-imports",
                headers={"Idempotency-Key": "acceptance-model"},
                json={
                    "name": "acceptance-model",
                    "servingBindingId": "local-process-serving",
                    "source": _hugging_face_source(),
                },
            )
            assert replay.status_code == 201
            assert replay.json()["id"] == model_import["id"]

            fetched = client.get(f"/api/v1/model-imports/{model_import['id']}")
            assert fetched.status_code == 200
            assert fetched.json() == model_import

            listed = client.get("/api/v1/model-imports")
            assert listed.status_code == 200
            assert [item["id"] for item in listed.json()] == [model_import["id"]]

            conflict = client.post(
                "/api/v1/model-imports",
                headers={"Idempotency-Key": "acceptance-model"},
                json={
                    "name": "other-model",
                    "servingBindingId": "local-process-serving",
                    "source": _hugging_face_source(),
                },
            )
            assert conflict.status_code == 409
            assert conflict.headers["content-type"].startswith("application/problem+json")
            assert conflict.json()["code"] == "REACTOR_IDEMPOTENCY_CONFLICT"
    finally:
        app.state.reactor_store.close()


def test_import_requires_a_pinned_revision(tmp_path: Path) -> None:
    engine = _TestServingExecutionPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=engine)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/model-imports",
                json={
                    "name": "floating",
                    "servingBindingId": "local-process-serving",
                    "source": {
                        "kind": "HUGGING_FACE",
                        "repository": "Qwen/Qwen2.5-1.5B-Instruct",
                        "revision": "main",
                    },
                },
            )
            assert response.status_code == 422
            assert response.headers["content-type"].startswith("application/problem+json")
            assert response.json()["code"] == "REACTOR_REQUEST_INVALID"
    finally:
        app.state.reactor_store.close()


def test_import_rejects_remote_code_and_relative_local_paths(tmp_path: Path) -> None:
    engine = _TestServingExecutionPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=engine)
    try:
        with TestClient(app) as client:
            remote_code = client.post(
                "/api/v1/model-imports",
                json={
                    "name": "remote-code",
                    "servingBindingId": "local-process-serving",
                    "source": _hugging_face_source(),
                    "trustRemoteCode": True,
                },
            )
            assert remote_code.status_code == 422
            assert remote_code.json()["code"] == "REACTOR_TRUST_REMOTE_CODE_FORBIDDEN"

            relative = client.post(
                "/api/v1/model-imports",
                json={
                    "name": "relative",
                    "servingBindingId": "local-process-serving",
                    "source": {"kind": "LOCAL_PATH", "path": "models/qwen"},
                },
            )
            assert relative.status_code == 422
            assert relative.json()["code"] == "REACTOR_REQUEST_INVALID"

            traversal = client.post(
                "/api/v1/model-imports",
                json={
                    "name": "traversal",
                    "servingBindingId": "local-process-serving",
                    "source": {"kind": "LOCAL_PATH", "path": "/srv/models/../secrets"},
                },
            )
            assert traversal.status_code == 422
            assert traversal.json()["code"] == "REACTOR_REQUEST_INVALID"
    finally:
        app.state.reactor_store.close()


def test_failed_import_is_persisted_with_a_diagnosable_problem(tmp_path: Path) -> None:
    engine = _TestServingExecutionPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=engine)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/model-imports",
                json={
                    "name": "missing",
                    "servingBindingId": "local-process-serving",
                    "source": {
                        "kind": "HUGGING_FACE",
                        "repository": "missing/model",
                        "revision": COMMIT,
                    },
                },
            )
            assert response.status_code == 503
            problem = response.json()
            assert problem["code"] == "REACTOR_MODEL_IMPORT_FAILED"
            assert problem["retryable"] is True

            persisted = client.get(problem["resourceRef"])
            assert persisted.status_code == 200
            assert persisted.json()["state"] == "FAILED"
            assert persisted.json()["failure"]["code"] == "REACTOR_MODEL_IMPORT_FAILED"
    finally:
        app.state.reactor_store.close()


def test_unknown_import_is_not_found(tmp_path: Path) -> None:
    engine = _TestServingExecutionPort()
    app = create_app(database_path=tmp_path / "reactor.sqlite3", engine=engine)
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/model-imports/11111111-1111-4111-8111-111111111111")
            assert response.status_code == 404
            assert response.json()["code"] == "REACTOR_MODEL_IMPORT_NOT_FOUND"
    finally:
        app.state.reactor_store.close()
