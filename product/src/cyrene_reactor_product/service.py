"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 service.py                                                      │
│  Module: cyrene_reactor_product.service                             │
│  Role: Product deployment and endpoint lifecycle authority.         │
│                                                                     │
│  模块职责：Deployment 与 Endpoint 生命周期权威及引擎协调。                 │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable
from threading import RLock
from typing import Any, cast
from uuid import UUID, uuid4

from cyrene_reactor_product.domain import (
    ArtifactRef,
    CreateDeploymentRequest,
    CreateModelImportRequest,
    Deployment,
    DeploymentEvent,
    DeploymentEventsResponse,
    DeploymentPhase,
    DesiredState,
    DiagnosticLevel,
    DiagnosticRecord,
    DiagnosticsPage,
    Endpoint,
    EndpointState,
    EngineHandle,
    ModelComposition,
    ModelImport,
    ModelImportState,
    ModelVersionDocument,
    NodeRef,
    ObservedState,
    ProductFailure,
    utc_now,
)
from cyrene_reactor_product.engine import ServingExecutionPort
from cyrene_reactor_product.errors import ReactorProductError, ServingEngineFailure
from cyrene_reactor_product.store import ReactorStore

# A deployment in one of these states will not produce more output on its own.
# 中文:处于这些状态之一的 Deployment 不会自行产生更多输出。
TERMINAL_OBSERVED_STATES = frozenset({ObservedState.STOPPED, ObservedState.FAILED})
DIAGNOSTICS_PAGE_MAX_BYTES = 1024 * 1024


def request_hash(command: CreateDeploymentRequest) -> str:
    """Hash a canonical request body for idempotency. | 生成幂等请求摘要。"""

    body = command.model_dump_json(by_alias=True, exclude_none=True)
    return hashlib.sha256(body.encode()).hexdigest()


def serving_artifact(deployment: Deployment) -> ArtifactRef:
    """Return the validated base/full projection used for placement.

    中文:返回供放置流程使用的已验证基础模型/完整模型投影。"""

    if deployment.model_artifact is None:
        raise ReactorProductError(
            code="REACTOR_MODEL_VERSION_INVALID",
            title="Model artifact projection missing",
            detail="A deployment must retain the full model or composed base artifact projection.",
            status=422,
        )
    return deployment.model_artifact


def serving_identity(deployment: Deployment) -> str:
    """Return the immutable identity expected in runtime readback.

    中文:返回运行时回读时应出现的不可变标识。"""

    if (
        deployment.composition == ModelComposition.BASE_PLUS_LORA
        and deployment.model_version is not None
    ):
        return str(deployment.model_version["id"])
    return serving_artifact(deployment).digest


def runtime_model_version(deployment: Deployment) -> ModelVersionDocument | None:
    """Pass a version to the runtime only for the composed serving path.

    中文:仅在组合模型服务路径中向运行时传递版本。"""

    if deployment.composition == ModelComposition.BASE_PLUS_LORA:
        return deployment.model_version
    return None


def _require_model_version_keyword(engine: Any, operation: str) -> None:
    """Reject an engine that cannot receive the composed model document.

    Signature inspection happens before the call so a missing legacy keyword is
    a stable unsupported-capability error.  A ``TypeError`` raised inside an
    otherwise compatible engine is intentionally allowed to propagate.

        中文:拒绝无法接收组合模型文档的引擎。

        中文：调用前会先检查方法签名,因此缺少旧版关键字参数会转化为稳定的“不支持此能力”错误。
        若兼容引擎内部抛出 ``TypeError``,则会按原样向上传播。
    """

    method = getattr(engine, operation, None)
    if method is None:
        raise ServingEngineFailure(
            f"COMPOSED_MODEL_BACKEND_UNSUPPORTED: engine {operation} must accept model_version",
            status=422,
        )
    try:
        parameters = inspect.signature(cast(Callable[..., Any], method)).parameters
    except (TypeError, ValueError) as exc:
        raise ServingEngineFailure(
            f"COMPOSED_MODEL_BACKEND_UNSUPPORTED: engine {operation} must accept model_version",
            status=422,
        ) from exc
    if "model_version" not in parameters and not any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    ):
        raise ServingEngineFailure(
            f"COMPOSED_MODEL_BACKEND_UNSUPPORTED: engine {operation} must accept model_version",
            status=422,
        )


def _fail_composed_identity(
    engine: Any,
    deployment: Deployment,
    model_version: ModelVersionDocument,
    handle: Any,
) -> None:
    """Clean up a start whose engine identity did not echo the canonical version.

    中文:清理启动后未回显规范版本标识的执行实例。"""

    execution_ref = getattr(handle, "execution_ref", None)
    endpoint_url = getattr(handle, "endpoint_url", None)
    expected_id = str(model_version["id"])
    cleanup_detail: str | None = None
    cleanup_retryable = False
    try:
        _require_model_version_keyword(engine, "stop")
        engine.stop(
            execution_ref,
            endpoint_url,
            deployment.id,
            expected_id,
            model_version=model_version,
        )
    except ServingEngineFailure as exc:
        cleanup_detail = str(exc)
        cleanup_retryable = exc.retryable
    detail = f"MODEL_VERSION_IDENTITY_MISMATCH: engine did not load {expected_id}"
    if cleanup_detail is not None:
        detail += f"; cleanup failed: {cleanup_detail}"
    raise ServingEngineFailure(
        detail,
        execution_ref=execution_ref,
        endpoint_url=endpoint_url,
        status=409,
        retryable=cleanup_retryable,
    )


def _verify_started_model_identity(
    engine: ServingExecutionPort, deployment_id: UUID, handle: EngineHandle
) -> None:
    """Run an adapter-specific serving registry readback after startup.

    中文:启动后执行适配器专属的服务注册表回读。"""

    verifier = getattr(engine, "verify_served_model", None)
    if callable(verifier):
        verifier(deployment_id, handle.execution_ref, handle.endpoint_url, handle.model)


def _cleanup_started_execution(
    engine: ServingExecutionPort,
    deployment: Deployment,
    handle: EngineHandle,
    model_digest: str,
    model_version: ModelVersionDocument | None,
) -> str | None:
    """Release a process that failed post-start identity verification.

    中文:释放启动后标识验证失败的进程。"""

    try:
        if model_version is not None:
            _require_model_version_keyword(engine, "stop")
        engine.stop(
            handle.execution_ref,
            handle.endpoint_url,
            deployment.id,
            model_digest,
            model_version=model_version,
        )
    except ServingEngineFailure as exc:
        return str(exc)
    return None


class ReactorService:
    """Own Product state while delegating serving execution. | 产品状态权威服务。"""

    def __init__(
        self,
        *,
        store: ReactorStore,
        engine: ServingExecutionPort,
        engines: dict[str, ServingExecutionPort] | None = None,
    ) -> None:
        self.store = store
        self.engine = engine
        self.engines = engines
        self._commands = RLock()

    def _append_deployment_event(
        self,
        deployment_id: UUID,
        phase: DeploymentPhase,
        message: str,
        failure_code: str | None = None,
    ) -> DeploymentEvent:
        return self.store.append_deployment_event(
            deployment_id=deployment_id,
            phase=phase,
            message=message,
            occurred_at=utc_now(),
            failure_code=failure_code,
        )

    def _engine(self, binding_id: str) -> ServingExecutionPort:
        if self.engines is None:
            return self.engine
        engine = self.engines.get(binding_id)
        if engine is None:
            raise ReactorProductError(
                code="REACTOR_BINDING_PERMISSION_DENIED",
                title="Serving binding unavailable",
                detail="Select a configured serving binding available to this workspace.",
                status=403,
            )
        return engine

    def create_deployment(
        self, command: CreateDeploymentRequest, idempotency_key: str | None
    ) -> Deployment:
        """Start and identity-check a new serving Deployment. | 启动并校验新部署。"""

        with self._commands:
            return self._create_deployment(command, idempotency_key)

    def create_model_import(
        self, command: CreateModelImportRequest, idempotency_key: str | None
    ) -> ModelImport:
        """Validate and persist an external model import. | 校验并持久化外部模型导入。"""

        with self._commands:
            if command.trust_remote_code:
                raise ReactorProductError(
                    code="REACTOR_TRUST_REMOTE_CODE_FORBIDDEN",
                    title="Remote code is not admitted",
                    detail=(
                        "trust_remote_code must remain disabled; this RC only imports "
                        "self-contained config, tokenizer, and weight files."
                    ),
                    status=422,
                )
            digest = hashlib.sha256(
                command.model_dump_json(by_alias=True, exclude_none=True).encode()
            ).hexdigest()
            replay_id = self.store.resolve_model_import_request(idempotency_key, digest)
            if replay_id is not None:
                return self._require_model_import(UUID(replay_id))
            engine = self._engine(command.serving_binding_id)
            now = utc_now()
            pending = ModelImport(
                id=uuid4(),
                name=command.name,
                serving_binding_id=command.serving_binding_id,
                source=command.source,
                credential_ref=command.credential_ref,
                state=ModelImportState.VALIDATING,
                created_at=now,
                updated_at=now,
                resource_version=1,
            )
            replay = self.store.commit_model_import_intent(pending, idempotency_key, digest)
            if replay is not None:
                return self._require_model_import(UUID(replay))
            try:
                result = engine.import_model(command)
            except ServingEngineFailure as exc:
                error = ReactorProductError(
                    code="REACTOR_MODEL_IMPORT_FAILED",
                    title="Model import failed",
                    detail=str(exc),
                    status=exc.status,
                    retryable=exc.retryable,
                    resource_ref=f"/api/v1/model-imports/{pending.id}",
                )
                failed = pending.model_copy(
                    update={
                        "state": ModelImportState.FAILED,
                        "failure": ProductFailure(
                            code=error.code,
                            message=error.detail,
                            retryable=error.retryable,
                        ),
                        "updated_at": utc_now(),
                        "resource_version": 2,
                    }
                )
                self.store.save_model_import(failed)
                raise error from exc
            ready = pending.model_copy(
                update={
                    "state": ModelImportState.READY,
                    "model_artifact": result.model_artifact,
                    "validation": result.validation,
                    "failure": None,
                    "updated_at": utc_now(),
                    "resource_version": 2,
                }
            )
            self.store.save_model_import(ready)
            return ready

    def get_model_import(self, model_import_id: UUID) -> ModelImport:
        """Read a persisted model import. | 读取持久化模型导入。"""

        with self._commands:
            return self._require_model_import(model_import_id)

    def list_model_imports(self) -> list[ModelImport]:
        """List persisted model imports. | 列出持久化模型导入。"""

        return self.store.list_model_imports()

    def _require_model_import(self, model_import_id: UUID) -> ModelImport:
        model_import = self.store.get_model_import(model_import_id)
        if model_import is None:
            raise ReactorProductError(
                code="REACTOR_MODEL_IMPORT_NOT_FOUND",
                title="Model import not found",
                detail="No ModelImport exists with the requested id.",
                status=404,
            )
        return model_import

    def _create_deployment(
        self, command: CreateDeploymentRequest, idempotency_key: str | None
    ) -> Deployment:

        digest = request_hash(command)
        replay_id = self.store.resolve_idempotency(idempotency_key, digest)
        if replay_id is not None:
            return self.get_deployment(UUID(replay_id))
        now = utc_now()
        deployment = Deployment(
            id=uuid4(),
            name=command.name,
            model_artifact=command.model_artifact,
            composition=command.composition,
            model_version=command.model_version,
            desired_state=DesiredState.ACTIVE,
            observed_state=ObservedState.STARTING,
            serving_binding_id=command.serving_binding_id,
            node_ref=command.node_ref,
            created_at=now,
            updated_at=now,
            resource_version=1,
        )
        self._engine(deployment.serving_binding_id)
        replay = self.store.create_intent(deployment, idempotency_key, digest)
        if replay is not None:
            return self.get_deployment(UUID(replay))
        self._append_deployment_event(deployment.id, DeploymentPhase.QUEUED, "Deployment queued")
        return self._launch(deployment)

    def _launch(self, deployment: Deployment) -> Deployment:
        self._append_deployment_event(
            deployment.id,
            DeploymentPhase.LOADING,
            f"Serving process starting on {deployment.serving_binding_id}",
        )
        prepared = self._engine(deployment.serving_binding_id).prepare(deployment.id)
        if prepared is not None:
            now = utc_now()
            previous = (
                self._require_endpoint(deployment.endpoint_id) if deployment.endpoint_id else None
            )
            pending = Endpoint(
                id=deployment.endpoint_id or uuid4(),
                deployment_id=deployment.id,
                state=EndpointState.PROVISIONING,
                url=prepared.endpoint_url,
                model=prepared.model,
                created_at=previous.created_at if previous else now,
                updated_at=now,
                resource_version=previous.resource_version + 1 if previous else 1,
            )
            deployment = deployment.model_copy(update={"endpoint_id": pending.id})
            self.store.save_pair(deployment, pending, execution_ref=prepared.execution_ref)
        engine: ServingExecutionPort | None = None
        handle: EngineHandle | None = None
        cleanup_handled = False
        model_version: ModelVersionDocument | None = None
        model: ArtifactRef | None = None
        try:
            model = serving_artifact(deployment)
            engine = self._engine(deployment.serving_binding_id)
            model_version = runtime_model_version(deployment)
            if model_version is None:
                handle = engine.start(deployment.id, model, node_ref=deployment.node_ref)
            else:
                _require_model_version_keyword(engine, "start")
                handle = engine.start(
                    deployment.id,
                    model,
                    node_ref=deployment.node_ref,
                    model_version=model_version,
                )
                if getattr(handle, "model_version_id", None) != model_version["id"]:
                    cleanup_handled = True
                    _fail_composed_identity(engine, deployment, model_version, handle)
            assert engine is not None and handle is not None
            self._append_deployment_event(
                deployment.id,
                DeploymentPhase.PROBING,
                "Waiting for inference readiness probe",
            )
            _verify_started_model_identity(engine, deployment.id, handle)
        except ServingEngineFailure as exc:
            cleanup_detail = None
            if (
                engine is not None
                and handle is not None
                and not cleanup_handled
                and model is not None
            ):
                cleanup_detail = _cleanup_started_execution(
                    engine,
                    deployment,
                    handle,
                    model_version["id"] if model_version is not None else model.digest,
                    model_version,
                )
            if cleanup_detail is not None:
                exc = ServingEngineFailure(
                    f"{exc}; cleanup failed: {cleanup_detail}",
                    execution_ref=exc.execution_ref,
                    endpoint_url=exc.endpoint_url,
                    status=exc.status,
                    retryable=True,
                )
            error = ReactorProductError(
                code="REACTOR_SERVING_START_FAILED",
                title="Serving startup failed",
                detail=str(exc),
                status=exc.status,
                retryable=exc.retryable,
                resource_ref=f"/api/v1/deployments/{deployment.id}",
            )
            failed = deployment.model_copy(
                update={
                    "observed_state": ObservedState.FAILED,
                    "failure": ProductFailure(
                        code=error.code,
                        message=error.detail,
                        retryable=error.retryable,
                    ),
                    "updated_at": utc_now(),
                    "resource_version": deployment.resource_version + 1,
                }
            )
            if exc.execution_ref is not None and exc.endpoint_url is not None:
                now = utc_now()
                previous = (
                    self._require_endpoint(deployment.endpoint_id)
                    if deployment.endpoint_id
                    else None
                )
                endpoint = Endpoint(
                    id=deployment.endpoint_id or uuid4(),
                    deployment_id=deployment.id,
                    state=EndpointState.UNHEALTHY,
                    url=exc.endpoint_url,
                    model=previous.model if previous else None,
                    created_at=previous.created_at if previous else now,
                    updated_at=now,
                    resource_version=previous.resource_version + 1 if previous else 1,
                )
                failed = failed.model_copy(update={"endpoint_id": endpoint.id})
                self.store.save_pair(failed, endpoint, execution_ref=exc.execution_ref)
            else:
                self.store.save_deployment(failed)
            self._append_deployment_event(
                deployment.id,
                DeploymentPhase.FAILED,
                str(exc),
                failure_code=error.code,
            )
            # The Product's own view of why it gave up belongs in the same
            # stream the runtime output lands in, so one page tells the story.
            # 中文:Product 对自身放弃原因的判断应与运行时输出写入同一数据流,以便单页记录完整经过。
            self.record_deployment_diagnostic(
                deployment.id,
                message=f"Serving startup failed: {exc}",
                level="error",
                code=error.code,
            )
            raise error from exc

        ready_at = utc_now()
        previous = (
            self._require_endpoint(deployment.endpoint_id) if deployment.endpoint_id else None
        )
        endpoint = Endpoint(
            id=deployment.endpoint_id or uuid4(),
            deployment_id=deployment.id,
            state=EndpointState.READY,
            url=handle.endpoint_url,
            model=handle.model,
            created_at=previous.created_at if previous else ready_at,
            updated_at=ready_at,
            resource_version=previous.resource_version + 1 if previous else 1,
        )
        ready = deployment.model_copy(
            update={
                "observed_state": ObservedState.READY,
                "endpoint_id": endpoint.id,
                "updated_at": ready_at,
                "failure": None,
                "resource_version": deployment.resource_version + 1,
            }
        )
        self.store.save_pair(ready, endpoint, execution_ref=handle.execution_ref)
        self._append_deployment_event(
            deployment.id,
            DeploymentPhase.READY,
            f"Model identity verified: {handle.model}",
        )
        self.record_deployment_diagnostic(
            deployment.id,
            message=f"Deployment ready: {handle.model}",
            level="info",
            code="REACTOR.DEPLOYMENT.READY",
        )
        return ready

    def get_deployment(self, deployment_id: UUID) -> Deployment:
        """Read and reconcile a Deployment from live engine evidence. | 读取并协调部署。"""

        deployment = self._require_deployment(deployment_id)
        if (
            deployment.observed_state in {ObservedState.READY, ObservedState.DEGRADED}
            and deployment.endpoint_id is not None
        ):
            endpoint = self._require_endpoint(deployment.endpoint_id)
            execution_ref = self.store.get_execution_ref(deployment.id)
            if execution_ref is None:
                return deployment
            model = serving_artifact(deployment)
            engine = self._engine(deployment.serving_binding_id)
            model_version = runtime_model_version(deployment)
            if model_version is None:
                observation = engine.inspect(
                    execution_ref,
                    endpoint.url,
                    deployment.id,
                    model.digest,
                )
            else:
                _require_model_version_keyword(engine, "inspect")
                observation = engine.inspect(
                    execution_ref,
                    endpoint.url,
                    deployment.id,
                    serving_identity(deployment),
                    model_version=model_version,
                )
            observed_state = ObservedState.READY if observation.ready else ObservedState.DEGRADED
            endpoint_state = EndpointState.READY if observation.ready else EndpointState.UNHEALTHY
            if observed_state != deployment.observed_state or endpoint_state != endpoint.state:
                version = deployment.resource_version
                now = utc_now()
                deployment = deployment.model_copy(
                    update={
                        "observed_state": observed_state,
                        "failure": None
                        if observation.ready
                        else ProductFailure(
                            code="REACTOR_EXECUTION_UNAVAILABLE",
                            message=observation.detail,
                            retryable=True,
                        ),
                        "updated_at": now,
                        "resource_version": deployment.resource_version + 1,
                    }
                )
                endpoint = endpoint.model_copy(
                    update={
                        "state": endpoint_state,
                        "updated_at": now,
                        "resource_version": endpoint.resource_version + 1,
                    }
                )
                with self._commands:
                    current = self._require_deployment(deployment.id)
                    if current.resource_version != version:
                        return current
                    self.store.save_pair(deployment, endpoint)
        return deployment

    def get_endpoint(self, endpoint_id: UUID) -> Endpoint:
        """Read an Endpoint after reconciling its Deployment. | 协调后读取 Endpoint。"""

        endpoint = self._require_endpoint(endpoint_id)
        self.get_deployment(endpoint.deployment_id)
        return self._require_endpoint(endpoint_id)

    def stop_deployment(self, deployment_id: UUID) -> Deployment:
        """Stop serving and retire the Endpoint without deleting evidence. | 停止并退役端点。"""

        with self._commands:
            return self._stop_deployment(deployment_id)

    def _stop_deployment(self, deployment_id: UUID) -> Deployment:
        deployment = self._require_deployment(deployment_id)
        if deployment.observed_state == ObservedState.STOPPED:
            return deployment
        now = utc_now()
        stopping = deployment.model_copy(
            update={
                "desired_state": DesiredState.STOPPED,
                "observed_state": ObservedState.STOPPING,
                "updated_at": now,
                "resource_version": deployment.resource_version + 1,
            }
        )
        self.store.save_deployment(stopping)
        self._append_deployment_event(
            deployment.id,
            DeploymentPhase.STOPPING,
            "Stopping deployment",
        )
        endpoint = (
            self._require_endpoint(deployment.endpoint_id)
            if deployment.endpoint_id is not None
            else None
        )
        execution_ref = self.store.get_execution_ref(deployment.id)
        if execution_ref is not None and endpoint is not None:
            try:
                model = serving_artifact(deployment)
                engine = self._engine(deployment.serving_binding_id)
                model_version = runtime_model_version(deployment)
                if model_version is None:
                    engine.stop(
                        execution_ref,
                        endpoint.url,
                        deployment.id,
                        model.digest,
                    )
                else:
                    _require_model_version_keyword(engine, "stop")
                    engine.stop(
                        execution_ref,
                        endpoint.url,
                        deployment.id,
                        serving_identity(deployment),
                        model_version=model_version,
                    )
            except ServingEngineFailure as exc:
                raise ReactorProductError(
                    code="REACTOR_SERVING_STOP_FAILED",
                    title="Serving stop failed",
                    detail=str(exc),
                    status=409,
                    retryable=True,
                    resource_ref=f"/api/v1/deployments/{deployment.id}",
                ) from exc
        stopped_at = utc_now()
        stopped = stopping.model_copy(
            update={
                "observed_state": ObservedState.STOPPED,
                "updated_at": stopped_at,
                "resource_version": stopping.resource_version + 1,
            }
        )
        if endpoint is None:
            self.store.save_deployment(stopped)
        else:
            retired = endpoint.model_copy(
                update={
                    "state": EndpointState.RETIRED,
                    "updated_at": stopped_at,
                    "resource_version": endpoint.resource_version + 1,
                }
            )
            self.store.save_pair(stopped, retired)
        self._append_deployment_event(
            deployment.id,
            DeploymentPhase.RELEASED,
            "Deployment stopped and resources released",
        )
        self.record_deployment_diagnostic(
            deployment.id,
            message="Deployment stopped and resources released",
            level="info",
            code="REACTOR.DEPLOYMENT.RELEASED",
        )
        return stopped

    def restart_deployment(
        self, deployment_id: UUID, node_ref: NodeRef, resource_version: int
    ) -> Deployment:
        """Restart after confirmed cleanup and node refresh. | 重启资源。"""
        with self._commands:
            deployment = self._require_deployment(deployment_id)
            if deployment.resource_version != resource_version:
                raise ReactorProductError(
                    code="REACTOR_VERSION_CONFLICT",
                    title="Deployment changed",
                    detail="Refresh the Deployment before restarting.",
                    status=409,
                )
            if deployment.observed_state != ObservedState.STOPPED:
                deployment = self.stop_deployment(deployment_id)
            starting = deployment.model_copy(
                update={
                    "node_ref": node_ref,
                    "desired_state": DesiredState.ACTIVE,
                    "observed_state": ObservedState.STARTING,
                    "failure": None,
                    "updated_at": utc_now(),
                    "resource_version": deployment.resource_version + 1,
                }
            )
            self.store.save_deployment(starting)
            self._append_deployment_event(
                deployment.id,
                DeploymentPhase.QUEUED,
                "Deployment restart queued",
            )
            return self._launch(starting)

    def deployment_events(self, deployment_id: UUID) -> DeploymentEventsResponse:
        """List chronological phase transition events for a deployment. | 列出部署阶段事件。"""
        self._require_deployment(deployment_id)
        events = self.store.list_deployment_events(deployment_id)
        return DeploymentEventsResponse(deployment_id=deployment_id, events=events)

    def record_deployment_diagnostic(
        self,
        deployment_id: UUID,
        *,
        message: str,
        level: DiagnosticLevel = "info",
        code: str | None = None,
    ) -> None:
        """Append one Product-owned diagnostic line for a lifecycle transition.

        中文:为一次生命周期转换追加一条由 Product 持有的诊断记录。"""

        self.store.append_deployment_diagnostics(
            deployment_id,
            [
                {
                    "timestamp": utc_now().isoformat(),
                    "level": level,
                    "source": "product",
                    "stream": "combined",
                    "code": code,
                    "message": message,
                    "resourceId": str(deployment_id),
                }
            ],
        )

    def deployment_diagnostics(
        self, deployment_id: UUID, *, after_sequence: int = 0, limit: int = 200
    ) -> DiagnosticsPage:
        """Harvest the runtime output and return one bounded, ordered page.

        中文:收集运行时输出并返回一页有界、按顺序排列的记录。"""

        if after_sequence < 0:
            raise ReactorProductError(
                code="REACTOR_DIAGNOSTICS_SEQUENCE_INVALID",
                title="Invalid diagnostics cursor",
                detail="afterSequence must be non-negative.",
                status=422,
            )
        deployment = self._require_deployment(deployment_id)
        degraded = self._harvest_runtime_diagnostics(deployment)
        records = self.store.list_deployment_diagnostics(deployment_id, after_sequence, limit)
        items = [DiagnosticRecord.model_validate(record) for record in records]
        items = _bound_diagnostics(items)
        return DiagnosticsPage(
            resource_id=str(deployment_id),
            items=items,
            next_sequence=items[-1].sequence if items else after_sequence,
            terminal=deployment.observed_state in TERMINAL_OBSERVED_STATES,
            diagnostics_degraded=(
                degraded or self.store.deployment_diagnostics_degraded(deployment_id)
            ),
        )

    def _harvest_runtime_diagnostics(self, deployment: Deployment) -> bool:
        """Persist new runtime records; report whether the binding could report.

        中文:持久化新的运行时记录,并报告绑定是否能提供这些记录。"""

        execution_ref = self.store.get_execution_ref(deployment.id)
        if execution_ref is None:
            return False
        engine = self._engine(deployment.serving_binding_id)
        reader = getattr(engine, "diagnostics", None)
        if reader is None:
            # A binding older than the diagnostics contract cannot report its
            # runtime output; say so instead of pretending the page is complete.
            # 中文:早于诊断契约的绑定无法提供运行时输出;应明确说明这一点,不能假装页面内容完整。
            return True
        cursor = self.store.runtime_diagnostics_cursor(deployment.id)
        page = reader(execution_ref, after_sequence=cursor, limit=500)
        if page is None:
            return True
        documents = []
        for record in page.get("items", []):
            if not isinstance(record, dict):
                continue
            documents.append(
                {
                    "timestamp": str(record.get("timestamp", "")),
                    "level": str(record.get("level", "info")),
                    "source": "runtime",
                    "stream": str(record.get("stream", "combined")),
                    "code": record.get("code"),
                    "message": str(record.get("message", ""))[:8192],
                    "requestId": record.get("requestId"),
                    "operationId": record.get("operationId"),
                    "resourceId": str(deployment.id),
                    "truncated": bool(record.get("truncated", False)),
                }
            )
        if page.get("diagnosticsDegraded") is True:
            documents.append(
                {
                    "timestamp": utc_now().isoformat(),
                    "level": "warn",
                    "source": "runtime",
                    "stream": "combined",
                    "code": "REACTOR.DIAGNOSTICS.DEGRADED",
                    "message": "The serving runtime could not keep all of its output.",
                    "resourceId": str(deployment.id),
                }
            )
        if documents:
            self.store.append_deployment_diagnostics(deployment.id, documents)
        next_sequence = page.get("nextSequence")
        if isinstance(next_sequence, int):
            self.store.set_runtime_diagnostics_cursor(deployment.id, next_sequence)
        return bool(page.get("diagnosticsDegraded") is True)

    def _require_deployment(self, deployment_id: UUID) -> Deployment:
        deployment = self.store.get_deployment(deployment_id)
        if deployment is None:
            raise ReactorProductError(
                code="REACTOR_DEPLOYMENT_NOT_FOUND",
                title="Deployment not found",
                detail="No Deployment exists with the requested id.",
                status=404,
            )
        return deployment

    def _require_endpoint(self, endpoint_id: UUID) -> Endpoint:
        endpoint = self.store.get_endpoint(endpoint_id)
        if endpoint is None:
            raise ReactorProductError(
                code="REACTOR_ENDPOINT_NOT_FOUND",
                title="Endpoint not found",
                detail="No Endpoint exists with the requested id.",
                status=404,
            )
        return endpoint


def _bound_diagnostics(items: list[DiagnosticRecord]) -> list[DiagnosticRecord]:
    """Trim one page to the serialized byte budget shared with the console.

    中文:按与控制台共用的序列化字节预算裁剪单页内容。"""

    kept = list(items)
    while (
        kept
        and len(
            json.dumps([item.model_dump(by_alias=True) for item in kept], separators=(",", ":"))
        )
        > DIAGNOSTICS_PAGE_MAX_BYTES
    ):
        kept.pop()
    return kept
