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
