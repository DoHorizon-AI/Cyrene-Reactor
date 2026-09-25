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
---
<!-- Chinese Translation / 中文翻译 -->

# Reactor 执行引擎 Plugin 端口

`ServingExecutionPort` 是 Reactor 内部应用边界，负责协调准备、启动、观测和停止。它不定义 Plugin 载荷，也不会发布另一套独立版本化的 SPI。

规范的 `execution.engine.v1` 契约与其实现一起由 Cyrene-Plugins-Official 持有：

- `contracts/capabilities.yaml` 记录契约 owner、版本和消费者；
- `plugins/engines/contracts/v1/schema.json` 定义方法载荷；
- `contracts/tck/owner-scoped-capabilities-v1` 将架构、清单和可调用实现绑定起来，无需检出 Platform。

Reactor 适配器从 Platform 获取通用本地连接，然后通过 Plugins 的 `DirectPluginClient` SDK 直接调用 Plugin 所有的契约。对于 JSON 能力方法，请求和响应字节使用规范的 `type.cyrene.io/{capability_id}.{method}.{request|response}` 类型 URL。Platform 可以安装、准入、启动和停止软件包，并报告健康状态；请求和响应载荷不会经过 Platform 进程。该端口可以返回内部证据，但只有 Reactor 会提交 `Deployment` 和 `Endpoint` 状态。

生产运行时仅支持 `DIRECT_PLUGIN`，并使用 Plugins 的 `DirectPluginClient`。Reactor 不包含仓库内引擎工厂或兼容回退。直连 `execution.engine.v1` Plugin 绑定不会改变 Product 生命周期权威。Exchange 也会直接调用自己的 Plugin 契约。

`prepare` 会在执行前持久化稳定且不透明的恢复句柄；`start` 要求当前有效的 NodeRef。只有从已配置绑定回读到身份信息后，才能进入 READY。即使推理服务已停止，`stop` 仍会使用该句柄，并要求明确确认资源已释放。Endpoint 版本会在重启间递增；提供方细节不会进入 Product 状态。
