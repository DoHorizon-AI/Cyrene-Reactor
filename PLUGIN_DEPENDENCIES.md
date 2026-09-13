# Plugin dependencies / 插件依赖

Reactor consumes the Plugins-owned direct transport SDK from the immutable
accepted Plugins revision below. It does not read a sibling Plugins checkout
at runtime and does not copy the execution-engine schema.

Reactor 使用下方 Plugins 已接受提交中的直连传输 SDK。运行时不读取相邻 Plugins
源码目录，也不复制 execution-engine schema。

| Package | Source | License status | Purpose |
|---|---|---|---|
| `cyrene-plugin-runtime` | `Cyrene-Plugins-Official@3afbac4d386eb7a27f6778149187884820c0b7f6`, `sdk/python/cyrene_plugin_runtime` | **UNDECLARED upstream** | `DirectPluginRuntime` gRPC client and typed payload facade |

`execution.engine.v1` payloads remain owned by Plugins. Reactor only encodes and
validates the owner-defined JSON bytes and canonical type URLs at its Product
port.

`execution.engine.v1` 的载荷仍由 Plugins 所有。Reactor 仅在 Product 端口编码、
校验 owner 定义的 JSON 字节及规范类型 URL。

The upstream SDK manifest currently has no SPDX license field. This is a
public dependency-closure blocker; Reactor's Apache-2.0 license does not
relicense the SDK. Resolve the upstream license metadata and anonymous clone
path before publishing this repository.

上游 SDK manifest 当前没有 SPDX 许可证字段。这是公开依赖闭包阻塞项；Reactor 的
Apache-2.0 不会重新授权 SDK。公开本仓库前必须补齐上游许可证元数据并确认可匿名克隆。
