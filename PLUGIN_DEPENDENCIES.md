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
---
<!-- Chinese Translation / 中文翻译 -->

# Plugin 依赖

Reactor 使用下方不可变且已接受的 Plugins 修订版本所拥有的直连传输 SDK。运行时不会读取相邻的 Plugins 检出目录，也不会复制执行引擎架构。

| 软件包 | 来源 | 许可证状态 | 用途 |
|---|---|---|---|
| `cyrene-plugin-runtime` | `Cyrene-Plugins-Official@3afbac4d386eb7a27f6778149187884820c0b7f6`，`sdk/python/cyrene_plugin_runtime` | **上游未声明** | `DirectPluginRuntime` gRPC 客户端和有类型载荷门面 |

`execution.engine.v1` 载荷仍由 Plugins 所有。Reactor 只在 Product 端口编码并验证由 owner 定义的 JSON 字节和规范类型 URL。

上游 SDK 清单目前没有 SPDX 许可证字段。这会阻止形成公开依赖闭包；Reactor 的 Apache-2.0 许可证不会重新授权该 SDK。公开发布此仓库前，必须补齐上游许可证元数据并确认可匿名克隆。
