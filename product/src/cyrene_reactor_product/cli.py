"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 cli.py                                                          │
│  Module: cyrene_reactor_product.cli                                 │
│  Role: Start the configured Reactor Product controller.            │
│  模块职责：启动 Reactor 产品控制端并消费外部服务绑定。                    │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

import uvicorn

from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.exchange_handoff import ExchangeHandoff, ExchangeReceiverConfiguration
from cyrene_reactor_product.remote_engine import (
    RemoteServingExecutionPort,
    ServingBindingConfiguration,
)


def main() -> None:
    """Run one Product scope with private credentials. | 启动一个产品作用域。"""
    parser = argparse.ArgumentParser(description="Reactor Product controller")
    parser.add_argument("mode", choices=["control", "init-secrets"])
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=19300, type=int)
    parser.add_argument("--tls-certificate", type=Path)
    parser.add_argument("--tls-key", type=Path)
    args = parser.parse_args()
    if args.mode == "init-secrets":
        args.config.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name, data in {"control.token": secrets.token_urlsafe(48).encode()}.items():
            fd = os.open(args.config / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(data)
        print("Created the private Product credential; no secret value was printed.")
        return
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not (
        args.tls_certificate and args.tls_key
    ):
        parser.error("Remote listeners require TLS; a loopback SSH tunnel is also supported")
    configuration = json.loads(args.config.read_text())
    bindings = [
        ServingBindingConfiguration.model_validate(item)
        for item in configuration["serving_bindings"]
    ]
    app = create_app(
        database_path=Path(configuration["database_path"]),
        credential_file=Path(configuration["credential_file"]),
        engines={binding.binding_id: RemoteServingExecutionPort(binding) for binding in bindings},
        exchange_receivers={
            receiver.receiver_id: ExchangeHandoff(receiver, configuration["public_base_url"])
            for receiver in (
                ExchangeReceiverConfiguration.model_validate(item)
                for item in configuration.get("exchange_receivers", [])
            )
        },
    )
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        ssl_certfile=str(args.tls_certificate) if args.tls_certificate else None,
        ssl_keyfile=str(args.tls_key) if args.tls_key else None,
    )


if __name__ == "__main__":
    main()
