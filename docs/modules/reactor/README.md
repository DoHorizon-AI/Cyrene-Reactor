# Reactor module / Reactor 模块

## Purpose / 目录用途

This module page is the entry point for Reactor's canonical serving runtime, optional extensions, and Rust integrations.

本模块页是 Reactor 标准服务运行时、可选扩展与 Rust 集成的入口。

## Files and responsibilities / 文件与职责

| Path | Responsibility / 职责 |
|---|---|
| [`core/README.md`](core/README.md) | Core runtime files, package boundary, and reading order / 核心运行时文件、包边界与阅读顺序 |
| [`pro/README.md`](pro/README.md) | Pro runtime files and explicit limitations / Pro 运行时文件与明确限制 |
| [`components/README.md`](components/README.md) | Platform placement adapter / Platform 放置适配器 |
| [`../../API.md`](../../API.md) | Serving objects, interfaces, and lifecycle contract / 服务对象、接口与生命周期契约 |
| [`../../architecture-and-lifecycle.md`](../../architecture-and-lifecycle.md) | Current architecture and ownership decisions / 当前架构与归属决策 |
| [`../../../service.json`](../../../service.json) | Service identity and declared extension points / 服务身份与已声明扩展点 |
| [`../../../repository-policy.yaml`](../../../repository-policy.yaml) | Repository lifecycle and governance metadata / 仓库生命周期与治理元数据 |

## Suggested reading / 推荐阅读

1. `docs/architecture/overview.md` — understand the serving lifecycle.
2. `runtime/core/README.md` — locate the canonical worker package.
3. `runtime/pro/README.md` — understand optional behavior and limitations.
4. `components/host-placement/README.md` — inspect the Platform placement adapter.
5. `docs/API.md` — verify contract names and statuses.

1. `docs/architecture/overview.md` —— 理解服务生命周期。
2. `runtime/core/README.md` —— 定位标准工作器包。
3. `runtime/pro/README.md` —— 理解可选行为与限制。
4. `components/host-placement/README.md` —— 查看 Platform 放置适配器。
5. `docs/API.md` —— 核对契约名称与状态。
