# Reactor Product contract v1

Status: `REFERENCE_MVP_READY`; the subprocess/HTTP adapter proves the Product
boundary, not production vLLM, KServe, GPU, or distributed reconciliation.

Reactor owns durable `Deployment` intent/observation and distinct `Endpoint`
resources. A serving engine owns model loading and request execution; it cannot
publish Product `READY` state. A Kernel operation or Node Agent report may be
evidence for reconciliation, but neither is the Deployment source of truth.

## Non-negotiable split

- `Deployment` is desired and observed Product lifecycle.
- `Endpoint` is an addressable serving surface with its own lifecycle. A ready
  Deployment may temporarily have an unhealthy Endpoint, and a stopped
  Deployment retains a retired Endpoint record for audit.
- `execution.engine.v1` is a Plugins-owned capability type. `servingBindingId` selects a bound
  capability instance; it is not a provider/package identity.
- Runtime execution evidence is stored in an internal adapter table and never
  appears in the public Deployment schema. It is not Product identity or state.
- Artifact bytes remain in the Artifact Plane; Deployment persists a model
  `ArtifactRef` only.
- `ModelVersion` is the Yield-owned immutable content identity. Reactor
  accepts `FULL_MODEL` compatibility requests and the V1 `BASE_PLUS_LORA`
  composition with exactly one base and one adapter; a composed Deployment's
  `modelArtifact` is only the base projection and `modelVersion.id` remains the
  serving identity.
- Events are notifications after Product commits, never the source of truth.

## Notifications

After durable commits, Reactor may publish created/updated notifications for
`deployment` and `endpoint`, using types such as
`dev.cyrene.reactor.deployment.updated.v1`. The common Product event envelope
contains only resource URI/version and change kind; consumers re-read Reactor
and tolerate duplicates, reordering, and newer versions. The local-process MVP
does not claim a durable outbox publisher.

## State

`Deployment.observedState`: `STARTING -> READY | FAILED`, `READY -> DEGRADED`,
and `READY | DEGRADED | FAILED -> STOPPING -> STOPPED`.

`Endpoint.state`: `PROVISIONING -> READY | UNHEALTHY -> RETIRED`.

On restart, Reactor validates persisted internal execution evidence and endpoint
identity through its local application port. It never infers `READY` from a
package, binding, PID, or Kernel lease alone. `serving-execution-port.md` maps
that local port to the Plugins-owned `execution.engine.v1` contract without
redefining it or proxying payloads through Platform.

## Compatibility

The API root is `/api/v1` and consumes the Workspace `product-http-v1`
compatibility profile, including deprecation and removal policy. OpenAPI is
3.1.2; JSON Schema is Draft 2020-12; errors follow RFC 9457.

The MVP is synchronous and returns `201`. A production reconciler may honor RFC
7240 and return `202` with `Location` naming the Product-owned Deployment. It
must not expose or create a second Kernel Operation API.

`Idempotency-Key` maps a create command to its durable Deployment before engine
startup. Replaying the same canonical body returns that Deployment's current
state, including `FAILED`; conflicting body reuse returns
`REACTOR_IDEMPOTENCY_CONFLICT`.

## Workspace private service routes

`workspace-private.openapi.yaml` defines private `GET` and `POST`
`/internal/workspace/v1/model-imports` routes. Product maps the bearer to a
fixed organization and Workspace using the server-side
`REACTOR_WORKSPACE_CREDENTIAL_MAP` JSON setting. It stores only SHA-256
digests, never bearer values. Tokens must be operator-generated random secrets
with at least 32 bytes of entropy. Distinct digests may map to the same scope
for rotation; duplicate digests and malformed maps are rejected. The map is
limited to 1,024 credentials and 256 KiB, and comparisons scan the full map.

```json
{"version":1,"credentials":[{"tokenSha256":"<lowercase SHA-256 hex>","organizationId":"org-id","workspaceId":"workspace-id"}]}
```

Private creates also require `REACTOR_WORKSPACE_SERVING_BINDING_GRANTS`. Its
operator-owned allowlist uses explicit `(servingBindingId, organizationId,
workspaceId)` triples; configured or historical bindings receive no implicit
grant:

```json
{"version":1,"grants":[{"servingBindingId":"serving-id","organizationId":"org-id","workspaceId":"workspace-id"}]}
```

Product assigns scope from this server-side map; the request body cannot
choose it. The `ModelImport`, trusted scope row, and optional idempotency
record are committed in one SQLite transaction. Private list reads join the
exact organization and Workspace scope. Legacy `/api/v1/model-imports` list
and get-by-id reads expose only unscoped imports; legacy-created imports remain
unscoped. Deployment and DeploymentDraft resources use separate tables and do
not resolve imports by ModelImport ID.

The private bearer authenticates the Platform service only, not a user,
Workspace member, or role. It is independent from the legacy `ControlBearer`.
Missing map configuration returns `503`, unknown bearers return `401`, and
malformed maps prevent startup. Missing legacy `credential_file` configuration
also fails closed with `503` on every non-health `/api/v1` route. Private
creates also require an explicit `REACTOR_WORKSPACE_SERVING_BINDING_GRANTS`
allowlist. Each grant binds one `servingBindingId` to one organization and
Workspace; existing bindings receive no implicit grant. An ungranted binding
returns `403` before import execution or Product writes. A missing allowlist
grants no private create access; malformed grant configuration prevents
startup. Anonymous legacy access
is available only when code explicitly sets `allow_unauthenticated_dev=True`
for local development or tests. Private routes still require their dedicated
credentials, and private creates require binding grants in that mode. The current Container Apps
workflow updates images but does not configure the ControlBearer, Workspace
credential map, or Workspace binding grant settings; operators must configure
them before production use. Create retains the existing `201` response and
optional `Idempotency-Key` behavior.
---
<!-- Chinese Translation / 中文翻译 -->

# Reactor Product 契约 v1

状态：`REFERENCE_MVP_READY`；子进程/HTTP 适配器证明的是 Product 边界，不代表生产 vLLM、KServe、GPU 或分布式 reconcile 已验收。

Reactor 持有持久化的 `Deployment` 意图/观测状态和独立的 `Endpoint` 资源。服务引擎负责模型加载和请求执行；它不能发布 Product 的 `READY` 状态。Kernel 操作或 Node Agent 报告可以作为 reconcile 证据，但两者都不是 Deployment 的事实源。

## 不可妥协的职责划分

- `Deployment` 表示期望和观测到的 Product 生命周期。
- `Endpoint` 是具有自身生命周期的可寻址服务接口。`Deployment` 就绪时 `Endpoint` 仍可能暂时不健康；`Deployment` 停止后会保留已退役的 `Endpoint` 记录供审计。
- `execution.engine.v1` 是由 Plugins 所有的能力类型。`servingBindingId` 选择一个已绑定的能力实例，不代表提供方或软件包身份。
- 运行时执行证据存放在内部适配器表中，绝不会出现在公开 Deployment 架构里；它不是 Product 标识或状态。
- Artifact 字节保留在 Artifact Plane；Deployment 只持久化模型 `ArtifactRef`。
- `ModelVersion` 是 Yield 所有的不可变内容标识。Reactor 接受 `FULL_MODEL` 兼容请求，以及恰好包含一个基础模型和一个适配器的 V1 `BASE_PLUS_LORA` 组合。组合 Deployment 的 `modelArtifact` 仅是基础模型投影，`modelVersion.id` 才是服务身份。
- 事件是在 Product 提交之后发出的通知，永远不是事实源。

## 通知

持久化提交后，Reactor 可以针对 `deployment` 和 `endpoint` 发布创建/更新通知，类型例如 `dev.cyrene.reactor.deployment.updated.v1`。通用 Product 事件封装只包含资源 URI/版本和变更类型；消费者应重新读取 Reactor，并容忍重复、乱序及更新版本。本地进程 MVP 不声称提供持久化 outbox 发布器。

## 状态

`Deployment.observedState`：`STARTING -> READY | FAILED`，`READY -> DEGRADED`，以及 `READY | DEGRADED | FAILED -> STOPPING -> STOPPED`。

`Endpoint.state`：`PROVISIONING -> READY | UNHEALTHY -> RETIRED`。

重启时，Reactor 通过本地应用端口验证持久化的内部执行证据和 endpoint 身份。它绝不会仅凭软件包、绑定、PID 或 Kernel lease 推断 `READY`。`serving-execution-port.md` 将该本地端口映射到 Plugins 所有的 `execution.engine.v1` 契约，不重新定义契约，也不经 Platform 代理载荷。

## 兼容性

API 根路径为 `/api/v1`，并采用 Workspace 的 `product-http-v1` 兼容配置，包括弃用和移除策略。OpenAPI 为 3.1.2；JSON Schema 为 Draft 2020-12；错误遵循 RFC 9457。

MVP 为同步接口并返回 `201`。生产 reconcile 可支持 RFC 7240，并返回 `202`，其中 `Location` 指向 Product 所有的 Deployment。不得暴露或创建第二套 Kernel Operation API。

`Idempotency-Key` 会在引擎启动前将创建命令映射到持久化 Deployment。重放相同规范请求体时返回该 Deployment 当前状态，包括 `FAILED`；若复用该键但请求体冲突，则返回 `REACTOR_IDEMPOTENCY_CONFLICT`。

## Workspace 私有服务路由

`workspace-private.openapi.yaml` 定义私有 `GET` 和 `POST /internal/workspace/v1/model-imports` 路由。Product 从服务端 `REACTOR_WORKSPACE_CREDENTIAL_MAP` JSON 配置将 Bearer 映射到固定组织和 Workspace。配置只保存 SHA-256 摘要，不保存 Bearer 明文。运维人员应生成至少 32 字节熵的随机 token。轮换时允许不同摘要映射到同一范围；重复摘要和格式错误的 map 会被拒绝。映射最多 1,024 个凭据、256 KiB，比较过程扫描完整映射。

```json
{"version":1,"credentials":[{"tokenSha256":"<小写 SHA-256 十六进制摘要>","organizationId":"组织 ID","workspaceId":"Workspace ID"}]}
```

私有创建还需要 `REACTOR_WORKSPACE_SERVING_BINDING_GRANTS`。其 operator-owned allowlist 只接受明确的 `(servingBindingId, organizationId, workspaceId)` 三元组；已配置或历史 binding 不会自动获得 grant：

```json
{"version":1,"grants":[{"servingBindingId":"serving-id","organizationId":"组织 ID","workspaceId":"Workspace ID"}]}
```

Product 从服务端映射赋予可信范围，body 不能选择范围。ModelImport、可信 scope 行和可选幂等记录在一个 SQLite 事务中提交。私有列表只通过组织和 Workspace 精确范围 JOIN 读取。旧 `/api/v1/model-imports` 列表和按 ID 读取只暴露无范围导入；legacy 创建的导入仍是无范围数据。Deployment 与 DeploymentDraft 使用独立表，不会通过 ModelImport ID 读取导入记录。

私有 Bearer 只认证 Platform 服务，不建立用户、Workspace 成员或角色身份；它与 legacy `ControlBearer` 分离。缺少 map 返回 `503`，未知 Bearer 返回 `401`，格式错误的 map 会阻止启动。私有创建还要求明确的 `REACTOR_WORKSPACE_SERVING_BINDING_GRANTS` allowlist；每条 grant 将 `servingBindingId` 固定绑定到一个组织和 Workspace，旧 binding 不会自动获得 grant。未授权的 binding 会在引擎执行和 Product 写入前返回 `403`。缺少 legacy `credential_file` 时，所有非健康检查 `/api/v1` 路由也会以 `503` 失败关闭。只有本地开发或测试代码显式设置 `allow_unauthenticated_dev=True` 才允许匿名 legacy 访问；该模式下私有路由仍需要专用 map，私有创建还需要 binding grants。当前 Container Apps workflow 只更新镜像，不配置 ControlBearer、Workspace map 或 Workspace binding grants；启用生产调用前，运维人员必须配置这些项。创建操作保留现有 `201` 响应和可选 `Idempotency-Key` 行为。
