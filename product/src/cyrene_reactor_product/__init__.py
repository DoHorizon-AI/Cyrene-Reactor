"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 __init__.py                                                     │
│  Module: cyrene_reactor_product                                     │
│  Role: Public Reactor Product API construction surface.              │
│                                                                     │
│  模块职责：导出 Reactor 产品 API 创建入口。                             │
└─────────────────────────────────────────────────────────────────────┘
"""

from cyrene_reactor_product.api import create_app

__all__ = ["create_app"]
