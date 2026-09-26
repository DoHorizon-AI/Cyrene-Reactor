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
from typing import Any
from uuid import UUID

import uvicorn

from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.engine import ServingExecutionPort
from cyrene_reactor_product.exchange_handoff import ExchangeHandoff, ExchangeReceiverConfiguration
from cyrene_reactor_product.remote_engine import (
    RemoteServingExecutionPort,
    ServingBindingConfiguration,
)
from cyrene_reactor_product.service import ReactorService
from cyrene_reactor_product.store import ReactorStore


def _configuration(path: Path) -> dict[str, Any]:
    """Read the private Product configuration shared by every command.

    中文:读取所有命令共用的私有 Product 配置。"""

    document = json.loads(path.read_text())
    if not isinstance(document, dict):
        raise ValueError("REACTOR_CONFIG_INVALID: expected a JSON object")
    return document


def _engines(configuration: dict[str, Any]) -> dict[str, ServingExecutionPort]:
    """Build one remote serving port per configured binding.

    中文:为每个已配置绑定构建一个远程服务端口。"""

    bindings = [
        ServingBindingConfiguration.model_validate(item)
        for item in configuration["serving_bindings"]
    ]
    return {binding.binding_id: RemoteServingExecutionPort(binding) for binding in bindings}


def _service(configuration: dict[str, Any]) -> ReactorService:
    """Build the Product service with its configured serving bindings.

    中文:使用已配置的服务绑定构建 Product 服务。"""

    engines = _engines(configuration)
    if not engines:
        raise ValueError("REACTOR_CONFIG_INVALID: at least one serving binding is required")
    return ReactorService(
        store=ReactorStore(Path(configuration["database_path"])),
        engine=next(iter(engines.values())),
        engines=engines,
    )


def _deployment_list(configuration: dict[str, Any]) -> int:
    store = ReactorStore(Path(configuration["database_path"]))
    try:
        payload = [
            {
                "id": str(deployment.id),
                "desiredState": deployment.desired_state.value,
                "observedState": deployment.observed_state.value,
                "servingBindingId": deployment.serving_binding_id,
                "endpointId": str(deployment.endpoint_id) if deployment.endpoint_id else None,
            }
            for deployment in store.list_deployments()
        ]
    finally:
        store.close()
    print(json.dumps({"object": "list", "data": payload}, indent=2))
    return 0


def _deployment_stop(configuration: dict[str, Any], deployment_id: UUID) -> int:
    service = _service(configuration)
    try:
        deployment = service.stop_deployment(deployment_id)
    finally:
        service.store.close()
    print(json.dumps({"id": str(deployment.id), "observedState": deployment.observed_state.value}))
    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Reactor Product controller")
    commands = value.add_subparsers(dest="mode", required=True)

    control = commands.add_parser("control", help="Serve the Reactor Product API")
    control.add_argument("--config", required=True, type=Path)
    control.add_argument("--host", default="127.0.0.1")
    control.add_argument("--port", default=19300, type=int)
    control.add_argument("--tls-certificate", type=Path)
    control.add_argument("--tls-key", type=Path)

    init = commands.add_parser("init-secrets", help="Create the private Product credential")
    init.add_argument("--config", required=True, type=Path)

    deployment = commands.add_parser("deployment", help="Inspect or stop deployments")
    deployment.add_argument("--config", required=True, type=Path)
    deployment_commands = deployment.add_subparsers(dest="deployment_command", required=True)
    deployment_commands.add_parser("list")
    stop = deployment_commands.add_parser("stop")
    stop.add_argument("--deployment-id", required=True, type=UUID)
    return value


def main() -> None:
    """Run one Product scope with private credentials. | 启动一个产品作用域。"""
    args = parser().parse_args()
    if args.mode == "init-secrets":
        args.config.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name, data in {"control.token": secrets.token_urlsafe(48).encode()}.items():
            fd = os.open(args.config / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(data)
        print("Created the private Product credential; no secret value was printed.")
        return
    configuration = _configuration(args.config)
    if args.mode == "deployment":
        if args.deployment_command == "list":
            raise SystemExit(_deployment_list(configuration))
        raise SystemExit(_deployment_stop(configuration, args.deployment_id))
    allow_insecure = os.environ.get("CYRENE_INSECURE_HTTP", "").lower() in {
        "1",
        "true",
        "yes",
    } or os.environ.get("REACTOR_ALLOW_INSECURE", "").lower() in {"1", "true", "yes"}
    if not allow_insecure and args.host not in {"127.0.0.1", "localhost", "::1"} and not (
        args.tls_certificate and args.tls_key
    ):
        raise SystemExit("Remote listeners require TLS; a loopback SSH tunnel is also supported")
    engines = _engines(configuration)
    app = create_app(
        database_path=Path(configuration["database_path"]),
        credential_file=Path(configuration["credential_file"]),
        engines=engines,
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
