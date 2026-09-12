# Reactor native components / Reactor 原生组件

## Purpose / 目录用途

This area contains the thin Rust adapter through which Reactor submits placement inputs to Platform.

本区域只保留 Reactor 向 Platform 提交放置输入的轻量 Rust 适配器。

## Files and responsibilities / 文件与职责

| Path | Responsibility / 职责 |
|---|---|
| [`../../../../components/host-placement/README.md`](../../../../components/host-placement/README.md) | Platform placement-adapter contract / Platform 放置适配器契约 |
| `components/host-placement/src/main.rs` | Adapter entrypoint; no placement or allocation authority / 适配器入口；不拥有放置或分配权威 |

## Suggested reading order / 推荐阅读顺序

1. `components/host-placement/README.md` — understand the authority boundary.
2. `components/host-placement/src/main.rs` — inspect the Platform adapter.

1. `components/host-placement/README.md` —— 理解权威边界。
2. `components/host-placement/src/main.rs` —— 查看 Platform 适配器。
