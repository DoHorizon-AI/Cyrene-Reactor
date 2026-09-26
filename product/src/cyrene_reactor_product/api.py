"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 api.py                                                          │
│  Module: cyrene_reactor_product.api                                 │
│  Role: Versioned HTTP adapter for Reactor Product resources.         │
│                                                                     │
│  模块职责：Reactor 产品资源的版本化 HTTP 适配器。                         │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import anyio
import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi import Path as ApiPath
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse

from cyrene_reactor_product.domain import (
    CreateDeploymentDraft,
    CreateDeploymentRequest,
    CreateModelImportRequest,
    DeployDraftRequest,
    Deployment,
    DeploymentDraft,
    DeploymentEventsResponse,
    DiagnosticsPage,
    Endpoint,
    ModelComposition,
    ModelImport,
    ProblemDetails,
    ProductResourceRef,
    RestartRequest,
    SendToExchangeRequest,
    utc_now,
)
from cyrene_reactor_product.engine import ServingExecutionPort, UnconfiguredServingExecutionPort
from cyrene_reactor_product.errors import (
    ReactorProductError,
    ServingEngineFailure,
    map_reactor_error,
)
from cyrene_reactor_product.exchange_handoff import ExchangeHandoff
from cyrene_reactor_product.logging import (
    bind_diagnostic_trace,
    emit_diagnostic_error,
    parse_w3c_traceparent,
    sanitize_request_id,
)
from cyrene_reactor_product.remote_engine import RemoteServingExecutionPort
from cyrene_reactor_product.service import ReactorService
from cyrene_reactor_product.store import ReactorStore


def create_app(
    *,
    database_path: Path,
    engine: ServingExecutionPort | None = None,
    engines: dict[str, ServingExecutionPort] | None = None,
    credential_file: Path | None = None,
    exchange_receivers: dict[str, ExchangeHandoff] | None = None,
) -> FastAPI:
    """Build Reactor with explicit Product and serving adapters. | 创建 Reactor 产品应用。"""

    store = ReactorStore(database_path)
    serving_engine = engine or UnconfiguredServingExecutionPort()
    service = ReactorService(store=store, engine=serving_engine, engines=engines)
    token = credential_file.read_text().strip() if credential_file else None
    if credential_file and (len(token or "") < 32 or credential_file.stat().st_mode & 0o077):
        raise ValueError("REACTOR_CREDENTIAL_INVALID")

    def authorize(request: Request) -> None:
        if request.url.path in {"/healthz", "/readyz", "/"}:
            return
        if token is not None and not secrets.compare_digest(
            request.headers.get("authorization", ""), "Bearer " + token
        ):
            raise HTTPException(403, "REACTOR_PERMISSION_DENIED")

    app = FastAPI(
        title="Cyrene Reactor Product API", version="1.0.0", dependencies=[Depends(authorize)]
    )

    @app.get("/healthz", include_in_schema=False)
    @app.get("/readyz", include_in_schema=False)
    @app.get("/", include_in_schema=False)
    def health_check() -> dict[str, str]:
        return {"status": "UP", "service": "cyrene-reactor"}

    app.state.reactor_store = store
    app.state.reactor_engine = serving_engine
    app.state.reactor_service = service

    @app.middleware("http")
    async def propagate_trace(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        parsed_trace = parse_w3c_traceparent(request.headers.get("traceparent"))
        trace_id = parsed_trace[0] if parsed_trace else uuid4().hex
        parent_span_id = parsed_trace[1] if parsed_trace else "0000000000000001"
        request_id = sanitize_request_id(request.headers.get("x-request-id")) or uuid4().hex

        request.state.trace_id = trace_id
        request.state.span_id = parent_span_id
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["traceparent"] = f"00-{trace_id}-0000000000000001-01"
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(ReactorProductError)
    async def product_error(request: Request, exc: ReactorProductError) -> JSONResponse:
        mapped = map_reactor_error(exc.code)
        canonical_code = mapped["code"]
        recovery_action = mapped.get("recovery_action")

        emit_diagnostic_error(
            "product.reactor.error",
            canonical_code,
            exc.detail,
            trace_id=getattr(request.state, "trace_id", None),
            span_id=getattr(request.state, "span_id", None),
            attributes={
                "request_id": getattr(request.state, "request_id", None),
                "cause_kind": mapped.get("cause_kind"),
                "status": exc.status,
                "path": request.url.path,
                "legacy_code": exc.code,
            },
        )

        problem = ProblemDetails(
            type=f"https://errors.cyrene.dev/reactor/{canonical_code.lower()}",
            title=exc.title,
            status=exc.status,
            detail=exc.detail,
            instance=request.url.path,
            code=exc.code,
            retryable=exc.retryable,
            trace_id=request.state.trace_id,
            resource_ref=exc.resource_ref,
            request_id=getattr(request.state, "request_id", None),
            recovery_action=recovery_action,
        )
        return JSONResponse(
            status_code=exc.status,
            content=problem.model_dump(by_alias=True, exclude_none=True, mode="json"),
            media_type="application/problem+json",
        )

    @app.exception_handler(ServingEngineFailure)
    async def binding_error(request: Request, exc: ServingEngineFailure) -> JSONResponse:
        return await product_error(
            request,
            ReactorProductError(
                code="REACTOR_BINDING_PERMISSION_DENIED"
                if exc.status == 403
                else "REACTOR_BINDING_UNAVAILABLE",
                title="Serving binding unavailable",
                detail=str(exc),
                status=exc.status,
                retryable=exc.retryable,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _exc: RequestValidationError) -> JSONResponse:
        mapped = map_reactor_error("REACTOR_REQUEST_INVALID")
        canonical_code = mapped["code"]
        recovery_action = mapped.get("recovery_action")

        emit_diagnostic_error(
            "product.reactor.validation_error",
            canonical_code,
            "The request does not conform to the Reactor Product API v1 contract.",
            trace_id=getattr(request.state, "trace_id", None),
            span_id=getattr(request.state, "span_id", None),
            attributes={
                "request_id": getattr(request.state, "request_id", None),
                "cause_kind": mapped.get("cause_kind"),
                "status": 422,
                "path": request.url.path,
            },
        )

        problem = ProblemDetails(
            type=f"https://errors.cyrene.dev/reactor/{canonical_code.lower()}",
            title="Request validation failed",
            status=422,
            detail="The request does not conform to the Reactor Product API v1 contract.",
            instance=request.url.path,
            code="REACTOR_REQUEST_INVALID",
            retryable=False,
            trace_id=request.state.trace_id,
            request_id=getattr(request.state, "request_id", None),
            recovery_action=recovery_action,
        )
        return JSONResponse(
            status_code=422,
            content=problem.model_dump(by_alias=True, mode="json"),
            media_type="application/problem+json",
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return await product_error(
            request,
            ReactorProductError(
                code=str(exc.detail),
                title="Reactor request rejected",
                detail=str(exc.detail),
                status=exc.status_code,
            ),
        )

    @app.post(
        "/api/v1/deployment-drafts",
        response_model=DeploymentDraft,
        status_code=201,
        response_model_exclude_none=True,
    )
    def import_draft(
        command: CreateDeploymentDraft,
        idempotency_key: str | None = Header(default=None, max_length=200),
    ) -> DeploymentDraft:
        identifier = uuid4()
        digest = hashlib.sha256(command.model_dump_json().encode()).hexdigest()
        draft = DeploymentDraft(
            **command.model_dump(),
            id=identifier,
            resource_ref=ProductResourceRef(
                uri=f"cyrene://reactor/deployment-drafts/{identifier}",
                id=identifier,
                resource_version=1,
            ),
            created_at=utc_now(),
        )
        return store.create_draft(draft, idempotency_key or "import:" + digest, digest)

    @app.get(
        "/api/v1/deployment-drafts",
        response_model=list[DeploymentDraft],
        response_model_exclude_none=True,
    )
    def list_drafts() -> list[DeploymentDraft]:
        return store.list_drafts()

    @app.get(
        "/api/v1/deployment-drafts/{draft_id}",
        response_model=DeploymentDraft,
        response_model_exclude_none=True,
    )
    def get_draft(draft_id: UUID) -> DeploymentDraft:
        return store.get_draft(draft_id)

    @app.post(
        "/api/v1/deployment-drafts/{draft_id}/actions/deploy",
        response_model=Deployment,
        response_model_exclude_none=True,
        status_code=201,
    )
    def deploy_draft(draft_id: UUID, command: DeployDraftRequest) -> Deployment:
        draft = store.get_draft(draft_id)
        deployment = service.create_deployment(
            CreateDeploymentRequest(**command.model_dump(), model_version=draft.model_version),
            "deployment-draft:" + str(draft_id),
        )
        draft.state = "STARTED"
        draft.deployment_ref = ProductResourceRef(
            uri=f"cyrene://reactor/deployments/{deployment.id}",
            id=deployment.id,
            resource_version=deployment.resource_version,
        )
        store.save_draft(draft)
        return deployment

    @app.post(
        "/api/v1/deployments",
        response_model=Deployment,
        response_model_exclude_none=True,
        status_code=201,
    )
    def create_deployment(
        command: CreateDeploymentRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=200),
    ) -> Deployment:
        return service.create_deployment(command, idempotency_key)

    @app.get(
        "/api/v1/deployments/{deploymentId}",
        response_model=Deployment,
        response_model_exclude_none=True,
    )
    def get_deployment(
        deployment_id: Annotated[UUID, ApiPath(alias="deploymentId")],
    ) -> Deployment:
        return service.get_deployment(deployment_id)

    @app.get(
        "/api/v1/deployments/{deploymentId}/events",
        response_model=DeploymentEventsResponse,
        response_model_exclude_none=True,
    )
    def deployment_events(
        deployment_id: Annotated[UUID, ApiPath(alias="deploymentId")],
    ) -> DeploymentEventsResponse:
        return service.deployment_events(deployment_id)

    @app.get(
        "/api/v1/deployments/{deploymentId}/diagnostics",
        response_model=DiagnosticsPage,
        response_model_exclude_none=True,
    )
    def deployment_diagnostics(
        request: Request,
        deployment_id: Annotated[UUID, ApiPath(alias="deploymentId")],
        after_sequence: int = Query(default=0, ge=0, alias="afterSequence"),
        limit: int = Query(default=200, ge=1, le=500),
    ) -> DiagnosticsPage:
        with bind_diagnostic_trace(request.state.trace_id, request.state.span_id):
            return service.deployment_diagnostics(
                deployment_id, after_sequence=after_sequence, limit=limit
            )

    @app.post(
        "/api/v1/deployments/{deploymentId}/actions/stop",
        response_model=Deployment,
        response_model_exclude_none=True,
    )
    def stop_deployment(
        deployment_id: Annotated[UUID, ApiPath(alias="deploymentId")],
    ) -> Deployment:
        return service.stop_deployment(deployment_id)

    @app.get("/api/v1/endpoints/{endpointId}", response_model=Endpoint)
    def get_endpoint(endpoint_id: Annotated[UUID, ApiPath(alias="endpointId")]) -> Endpoint:
        return service.get_endpoint(endpoint_id)

    @app.get("/api/v1/exchange-receivers")
    def receivers() -> list[dict[str, object]]:
        return [
            {
                "receiverId": name,
                "providerBindingIds": sorted(receiver.configuration.allowed_binding_ids),
            }
            for name, receiver in (exchange_receivers or {}).items()
        ]

    @app.post("/api/v1/endpoints/{endpointId}/actions/send-to-exchange", status_code=201)
    def send_to_exchange(
        endpoint_id: Annotated[UUID, ApiPath(alias="endpointId")],
        command: SendToExchangeRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=200),
    ) -> dict[str, object]:
        if not idempotency_key or not idempotency_key.strip():
            raise ReactorProductError(
                code="REACTOR_IDEMPOTENCY_KEY_REQUIRED",
                title="Idempotency key required",
                detail="Provide a stable Idempotency-Key for this explicit send operation.",
                status=422,
            )
        receiver = (exchange_receivers or {}).get(command.receiver_id)
        if receiver is None:
            raise ReactorProductError(
                code="REACTOR_RECEIVER_PERMISSION_DENIED",
                title="Receiver unavailable",
                detail="Select an Exchange receiver admitted for this workspace.",
                status=403,
            )
        return receiver.send(service, endpoint_id, command, idempotency_key)

    @app.get(
        "/api/v1/deployments", response_model=list[Deployment], response_model_exclude_none=True
    )
    def list_deployments() -> list[Deployment]:
        return store.list_deployments()

    @app.post(
        "/api/v1/model-imports",
        response_model=ModelImport,
        response_model_exclude_none=True,
        status_code=201,
    )
    def create_model_import(
        command: CreateModelImportRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=200),
    ) -> ModelImport:
        return service.create_model_import(command, idempotency_key)

    @app.get(
        "/api/v1/model-imports",
        response_model=list[ModelImport],
        response_model_exclude_none=True,
    )
    def list_model_imports() -> list[ModelImport]:
        return service.list_model_imports()

    @app.get(
        "/api/v1/model-imports/{importId}",
        response_model=ModelImport,
        response_model_exclude_none=True,
    )
    def get_model_import(
        import_id: Annotated[UUID, ApiPath(alias="importId")],
    ) -> ModelImport:
        return service.get_model_import(import_id)

    @app.get("/api/v1/deployments/{deploymentId}/export")
    def export_deployment(
        deployment_id: Annotated[UUID, ApiPath(alias="deploymentId")],
    ) -> dict[str, object]:
        deployment = service.get_deployment(deployment_id)
        return {
            "format": "cyrene.reactor.deployment.v1",
            "deployment": deployment.model_dump(mode="json", exclude_none=True),
            "endpoint": service.get_endpoint(deployment.endpoint_id).model_dump(mode="json")
            if deployment.endpoint_id
            else None,
        }

    @app.get("/api/v1/deployments/{deploymentId}/model-export")
    async def export_model(
        deployment_id: Annotated[UUID, ApiPath(alias="deploymentId")],
    ) -> StreamingResponse:
        deployment = store.get_deployment(deployment_id)
        if deployment is None:
            raise ReactorProductError(
                code="REACTOR_DEPLOYMENT_NOT_FOUND",
                title="Deployment not found",
                detail="Open an existing Deployment before exporting its model.",
                status=404,
            )
        if deployment.composition == ModelComposition.BASE_PLUS_LORA:
            raise ReactorProductError(
                code="COMPOSED_MODEL_EXPORT_UNSUPPORTED",
                title="Composed model export is unsupported",
                detail=(
                    "Exporting a BASE_PLUS_LORA projection as a full model is unsupported; "
                    "use a future merge/export task to create a new FULL_MODEL ModelVersion."
                ),
                status=409,
            )
        if deployment.model_artifact is None:
            raise ReactorProductError(
                code="REACTOR_MODEL_VERSION_INVALID",
                title="Model artifact projection missing",
                detail="The Deployment has no exportable full/base artifact projection.",
                status=422,
            )
        selected = remote(deployment.serving_binding_id)
        client = httpx.AsyncClient(timeout=httpx.Timeout(1900, connect=5), trust_env=False)
        try:
            upstream = await client.send(
                client.build_request(
                    "POST",
                    selected.binding.control_url.rstrip("/") + "/exports",
                    json=deployment.model_artifact.model_dump(mode="json"),
                    headers={"Authorization": "Bearer " + selected.token},
                ),
                stream=True,
            )
            upstream.raise_for_status()
        except httpx.HTTPError as exc:
            await client.aclose()
            raise ReactorProductError(
                code="REACTOR_MODEL_EXPORT_UNAVAILABLE",
                title="Model export unavailable",
                detail="Restore the execution binding and model Artifact access, then retry.",
                status=503,
                retryable=True,
            ) from exc

        async def chunks() -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            finally:
                with anyio.CancelScope(shield=True):
                    await upstream.aclose()
                    await client.aclose()

        return StreamingResponse(
            chunks(),
            media_type="application/x-tar",
            headers={"Content-Disposition": 'attachment; filename="model.tar"'},
        )

    @app.post(
        "/api/v1/deployments/{deploymentId}/actions/restart",
        response_model=Deployment,
        response_model_exclude_none=True,
    )
    def restart(
        deployment_id: Annotated[UUID, ApiPath(alias="deploymentId")], command: RestartRequest
    ) -> Deployment:
        return service.restart_deployment(deployment_id, command.node_ref, command.resource_version)

    configured_engines = engines or {}

    def remote(binding_id: str) -> RemoteServingExecutionPort:
        selected = configured_engines.get(binding_id)
        if not isinstance(selected, RemoteServingExecutionPort):
            raise HTTPException(403, "REACTOR_BINDING_PERMISSION_DENIED")
        return selected

    @app.get("/api/v1/serving-bindings")
    def bindings() -> list[dict[str, object]]:
        return [{"bindingId": binding_id} for binding_id in configured_engines]

    @app.get("/api/v1/serving-bindings/{binding_id}/node")
    def node(binding_id: str) -> dict[str, object]:
        return remote(binding_id).request("GET", "/node")

    return app
