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
import re
import secrets
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import uvicorn

from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.engine import ServingExecutionPort
from cyrene_reactor_product.exchange_handoff import ExchangeHandoff, ExchangeReceiverConfiguration
from cyrene_reactor_product.package_runtime_owner import package_runtime_engine
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
    """Build static or owner-resolved serving ports for configured bindings.

    PackageRuntime entries are resolved only from their authenticated runtime
    receipt. A configured package binding that cannot be admitted fails startup
    and never falls back to a static URL.

    中文:静态绑定保持兼容;包绑定只能由授权回执解析,失败时不回退。
    """

    bindings = [
        ServingBindingConfiguration.model_validate(item)
        for item in configuration.get("serving_bindings", [])
    ]
    engines: dict[str, ServingExecutionPort] = {
        binding.binding_id: RemoteServingExecutionPort(binding) for binding in bindings
    }
    if "package_runtime_bindings" not in configuration:
        return engines

    package_bindings = configuration["package_runtime_bindings"]
    if not isinstance(package_bindings, dict) or not package_bindings:
        raise ValueError("REACTOR_PACKAGE_RUNTIME_BINDINGS_INVALID")
    for binding_id, owner_configuration in package_bindings.items():
        if binding_id in engines:
            raise ValueError("REACTOR_PACKAGE_RUNTIME_BINDING_DUPLICATE")
        engines[binding_id] = package_runtime_engine(binding_id, owner_configuration)
    return engines


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


def _package_binding(
    configuration: dict[str, Any],
    command: str,
    request_id: str | None,
    installation_id: str | None = None,
) -> int:
    """Forward an owner lifecycle command to the authenticated Reactor API."""

    binding_id = os.environ.get("REACTOR_PACKAGE_RUNTIME_BINDING_ID", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][a-z0-9_.-]{1,127}", binding_id):
        raise SystemExit("PACKAGE_RUNTIME_BINDING_NOT_CONFIGURED")
    request_id = request_id or str(uuid4())
    base_url = str(configuration.get("control_url", "http://127.0.0.1:19300")).rstrip("/")
    credential_path = Path(configuration["credential_file"])
    token = credential_path.read_text(encoding="utf-8").strip()
    if len(token) < 32 or credential_path.stat().st_mode & 0o077:
        raise SystemExit("REACTOR_CONTROL_AUTH_UNAVAILABLE")
    url = f"{base_url}/api/v1/runtime-bindings/{binding_id}"
    headers = {"Authorization": f"Bearer {token}"}
    if command == "status":
        method, suffix, body = "GET", "", None
    else:
        method = "POST"
        suffix = f"/actions/{command}"
        headers["Idempotency-Key"] = request_id
        body = {"installationId": installation_id} if command == "activate" else None
        if command == "activate" and not body["installationId"]:
            raise SystemExit("PACKAGE_RUNTIME_INSTALLATION_ID_REQUIRED")
    # Print only the safe request identity before making the call so a caller can reconcile it.
    if command != "status":
        print(json.dumps({"requestId": request_id}))
    try:
        response = httpx.request(method, url + suffix, headers=headers, json=body, timeout=30.0)
    except httpx.HTTPError:
        print(
            json.dumps(
                {"requestId": request_id, "phase": "UNKNOWN", "code": "REACTOR_API_UNAVAILABLE"}
            )
        )
        return 2
    try:
        payload = response.json()
    except ValueError:
        payload = {"code": "REACTOR_API_RESPONSE_INVALID"}
    if isinstance(payload, dict):
        safe_payload = {
            key: payload[key]
            for key in (
                "bindingId",
                "requestId",
                "installationId",
                "phase",
                "blocked",
                "runtimeState",
                "code",
            )
            if key in payload and isinstance(payload[key], (str, int, float, bool, type(None)))
        }
    else:
        safe_payload = {"code": "REACTOR_API_RESPONSE_INVALID"}
    print(json.dumps(safe_payload, indent=2))
    return 0 if response.is_success else 2


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

    package_binding = commands.add_parser(
        "package-binding", help="Manage the configured PackageRuntime binding"
    )
    package_binding.add_argument("--config", required=True, type=Path)
    package_commands = package_binding.add_subparsers(dest="package_binding_command", required=True)
    activate = package_commands.add_parser("activate")
    activate.add_argument("--installation-id", required=True)
    reconcile = package_commands.add_parser("reconcile")
    reconcile.add_argument("--request-id", required=True)
    package_commands.add_parser("status")
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
    if args.mode == "package-binding":
        request_id = getattr(args, "request_id", None)
        raise SystemExit(
            _package_binding(
                configuration,
                args.package_binding_command,
                request_id,
                getattr(args, "installation_id", None),
            )
        )
    if args.mode == "deployment":
        if args.deployment_command == "list":
            raise SystemExit(_deployment_list(configuration))
        raise SystemExit(_deployment_stop(configuration, args.deployment_id))
    allow_insecure = os.environ.get("CYRENE_INSECURE_HTTP", "").lower() in {
        "1",
        "true",
        "yes",
    } or os.environ.get("REACTOR_ALLOW_INSECURE", "").lower() in {"1", "true", "yes"}
    if (
        not allow_insecure
        and args.host not in {"127.0.0.1", "localhost", "::1"}
        and not (args.tls_certificate and args.tls_key)
    ):
        raise SystemExit("Remote listeners require TLS; a loopback SSH tunnel is also supported")
    engines = _engines(configuration)
    app = create_app(
        database_path=Path(configuration["database_path"]),
        credential_file=Path(configuration["credential_file"]),
        workspace_credential_map_json=os.environ.get("REACTOR_WORKSPACE_CREDENTIAL_MAP"),
        workspace_serving_binding_grants_json=os.environ.get(
            "REACTOR_WORKSPACE_SERVING_BINDING_GRANTS"
        ),
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
