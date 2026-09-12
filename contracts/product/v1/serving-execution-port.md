# Reactor execution-engine Plugin port

`ServingExecutionPort` is Reactor's internal application boundary for
prepare/start/observe/stop orchestration. It does not define Plugin payloads or
publish another independently versioned SPI.

The canonical `execution.engine.v1` contract is owned beside the implementation
in Cyrene-Plugins-Official:

- `contracts/capabilities.yaml` records its owner, version and consumer;
- `plugins/engines/contracts/v1/schema.json` owns method payloads;
- `contracts/tck/owner-scoped-capabilities-v1` binds the schema, manifest and
  callable implementation without a Platform checkout.

A Reactor adapter obtains a generic local connection from Platform, then invokes
the Plugin-owned contract directly through the Plugins `DirectPluginClient` SDK.
For JSON capability methods, request and response bytes use the canonical
`type.cyrene.io/{capability_id}.{method}.{request|response}` type URL shape.
Platform may install, admit, start, stop and report health for the package;
request and response payloads do not pass through a Platform process. The port
may return internal evidence, but Reactor alone commits `Deployment` and
`Endpoint` state.

The production runtime supports only `DIRECT_PLUGIN` and uses the Plugins
`DirectPluginClient`. Reactor has no in-tree engine factory or compatibility
fallback. A direct `execution.engine.v1` Plugin binding does not change Product
lifecycle authority. Exchange invokes its own Plugin contracts directly.

`prepare` persists a stable opaque recovery handle before execution; `start`
requires a current NodeRef. READY requires identity readback from the configured
binding. `stop` uses that handle even when inference is down and requires explicit
release confirmation. Endpoint versions increase across restarts; provider
details remain outside Product state.

生产运行时只支持 `DIRECT_PLUGIN`，通过 Plugins 的 `DirectPluginClient` 直连；不再有
本地引擎工厂或兼容回退。JSON 能力方法使用规范
`type.cyrene.io/{capability_id}.{method}.{request|response}` 类型 URL。
Platform 只负责资源、准入和通用生命周期事实；Reactor 直接调用 Plugins 所有的
`execution.engine.v1` 契约，不会经由 Platform 代理业务负载，也不会另建
Deployment、Lease 或路由状态权威。
