# Architecture documentation / 架构文档

This directory explains Reactor's serving lifecycle, capability system, and protocol boundaries.

本目录说明 Reactor 的服务生命周期、能力系统与协议边界。

| File | Responsibility / 职责 |
|---|---|
| [`overview.md`](overview.md) | Runtime topology, request flow, lifecycle, and ownership / 运行时拓扑、请求流、生命周期与职责 |
| [`tool-system.md`](tool-system.md) | Engine provider seam, bounded request queue, and Platform placement adapter / 引擎提供方接缝、有界请求队列与 Platform 放置适配器 |
| [`mcp-integration.md`](mcp-integration.md) | MCP-facing boundary for tools or model-facing adapters / 面向工具或模型适配器的 MCP 边界 |

## Suggested reading order / 推荐阅读顺序

Read `overview.md` first, then `tool-system.md`, and consult `mcp-integration.md` when reviewing an external protocol adapter.

先阅读 `overview.md`，再阅读 `tool-system.md`；评审外部协议适配器时查阅 `mcp-integration.md`。
