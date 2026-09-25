"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 errors.py                                                       │
│  Module: cyrene_reactor_product.errors                              │
│  Role: Stable Product errors and sanitized serving failures.        │
│                                                                     │
│  模块职责：稳定产品错误与已净化服务引擎失败。                            │
└─────────────────────────────────────────────────────────────────────┘
"""


class ReactorProductError(RuntimeError):
    """Typed error exposed through the Product API. | 产品 API 类型化错误。"""

    def __init__(
        self,
        *,
        code: str,
        title: str,
        detail: str,
        status: int,
        retryable: bool = False,
        resource_ref: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.title = title
        self.detail = detail
        self.status = status
        self.retryable = retryable
        self.resource_ref = resource_ref


class ServingEngineFailure(RuntimeError):
    """Sanitized replaceable-engine failure. | 可替换服务引擎失败。"""

    def __init__(
        self,
        detail: str,
        *,
        execution_ref: str | None = None,
        endpoint_url: str | None = None,
        status: int = 422,
        retryable: bool = False,
    ) -> None:
        super().__init__(detail)
        self.execution_ref = execution_ref
        self.endpoint_url = endpoint_url
        self.status = status
        self.retryable = retryable


# ════════════════════════════════════════════════════════════════════════
# Canonical Cyrene Reactor Error Catalog & Mappings
# 规范 Cyrene Reactor 错误命名空间与恢复动作映射
# ════════════════════════════════════════════════════════════════════════
REACTOR_ERROR_MAPPINGS: dict[str, dict[str, str]] = {
    "REACTOR_PERMISSION_DENIED": {
        "code": "PRODUCT.REACTOR.PERMISSION_DENIED",
        "cause_kind": "permission",
        "recovery_action": "fix_configuration",
    },
    "REACTOR_CREDENTIAL_INVALID": {
        "code": "PRODUCT.REACTOR.CREDENTIAL_INVALID",
        "cause_kind": "credential",
        "recovery_action": "fix_configuration",
    },
    "REACTOR_REQUEST_INVALID": {
        "code": "PRODUCT.REACTOR.REQUEST_INVALID",
        "cause_kind": "validation",
        "recovery_action": "fix_configuration",
    },
    "REACTOR_BINDING_PERMISSION_DENIED": {
        "code": "PRODUCT.REACTOR.BINDING_PERMISSION_DENIED",
        "cause_kind": "permission",
        "recovery_action": "fix_configuration",
    },
    "REACTOR_BINDING_UNAVAILABLE": {
        "code": "PRODUCT.REACTOR.BINDING_UNAVAILABLE",
        "cause_kind": "infrastructure",
        "recovery_action": "query_state_first",
    },
    "REACTOR_DEPLOYMENT_NOT_FOUND": {
        "code": "PRODUCT.REACTOR.DEPLOYMENT_NOT_FOUND",
        "cause_kind": "not_found",
        "recovery_action": "user_action_required",
    },
    "REACTOR_DEPLOYMENT_DRAFT_NOT_FOUND": {
        "code": "PRODUCT.REACTOR.DEPLOYMENT_DRAFT_NOT_FOUND",
        "cause_kind": "not_found",
        "recovery_action": "user_action_required",
    },
    "REACTOR_MODEL_IMPORT_NOT_FOUND": {
        "code": "PRODUCT.REACTOR.MODEL_IMPORT_NOT_FOUND",
        "cause_kind": "not_found",
        "recovery_action": "user_action_required",
    },
    "REACTOR_MODEL_IMPORT_FAILED": {
        "code": "PRODUCT.REACTOR.MODEL_IMPORT_FAILED",
        "cause_kind": "execution",
        "recovery_action": "fix_configuration",
    },
    "REACTOR_IDEMPOTENCY_CONFLICT": {
        "code": "PRODUCT.REACTOR.IDEMPOTENCY_CONFLICT",
        "cause_kind": "conflict",
        "recovery_action": "safely_retry",
    },
    "REACTOR_HANDOFF_FAILED": {
        "code": "PRODUCT.REACTOR.HANDOFF_FAILED",
        "cause_kind": "network",
        "recovery_action": "safely_retry",
    },
    "REACTOR_INTERNAL_ERROR": {
        "code": "PRODUCT.REACTOR.INTERNAL_ERROR",
        "cause_kind": "internal",
        "recovery_action": "query_state_first",
    },
}


def map_reactor_error(raw_code: str) -> dict[str, str]:
    """Map a raw or legacy Reactor error code to canonical PRODUCT.REACTOR.<REASON>.

    中文:将原始或旧版 Reactor 错误码映射为规范的 PRODUCT.REACTOR.<REASON>。"""
    if raw_code in REACTOR_ERROR_MAPPINGS:
        return REACTOR_ERROR_MAPPINGS[raw_code]
    normalized = raw_code.upper().replace(" ", "_")
    if not normalized.startswith("PRODUCT.REACTOR."):
        clean_name = normalized.removeprefix("REACTOR_")
        canonical = f"PRODUCT.REACTOR.{clean_name}"
    else:
        canonical = normalized
    return {
        "code": canonical,
        "cause_kind": "unknown",
        "recovery_action": "query_state_first",
    }
