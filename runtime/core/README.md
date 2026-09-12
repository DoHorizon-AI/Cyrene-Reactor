# Reactor runtime core (`cy-exec`)

This package owns Reactor's Product-side inference coordination and generated
protocol bindings. Concrete vLLM, TensorRT-LLM, Ascend/MindIE, and other
execution engines are owned by `Cyrene-Plugins-Official`; this package keeps
only the Product port and its direct-runtime adapter. The checked-in
`src/cy_exec/proto` bindings are derived from the workspace contract;
regenerate them with the repository's contract tooling when the proto schema
changes.

## Plugin binding / 插件绑定

The production default is `DIRECT_PLUGIN`. Reactor requires a Platform-resolved
`CYRENE_SERVING_CONNECTION_REF` and invokes the Plugins-owned
`execution.engine.v1` contract through the immutable `cyrene-plugin-runtime`
SDK pinned in `pyproject.toml`. JSON capability payloads use the canonical
`type.cyrene.io/execution.engine.v1.<method>.<request|response>` type URLs;
there is no HTTP or Platform business-data proxy in this seam.

生产默认 profile 为 `DIRECT_PLUGIN`。Reactor 必须拿到 Platform 解析出的
`CYRENE_SERVING_CONNECTION_REF`，并通过 `pyproject.toml` 中固定版本的
`cyrene-plugin-runtime` SDK 直连 Plugins 所有的 `execution.engine.v1` 契约。
JSON 能力载荷使用规范 `type.cyrene.io/execution.engine.v1.<method>.<request|response>`
类型 URL；该接缝不使用 HTTP，也不经过 Platform 业务数据代理。

A missing binding or any direct SDK, transport, failure, deadline,
cancellation, or protocol/type-URL error raises `ServingPortFailure`. Reactor
has no in-tree execution-engine fallback.

绑定缺失以及直连 SDK、传输、失败、超时、取消或协议/类型 URL 错误都会抛出
`ServingPortFailure`。Reactor 不再包含本地执行引擎回退路径。
