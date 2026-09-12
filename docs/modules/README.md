# Module documentation / 模块文档

This directory maps Reactor's three active implementation areas.

本目录梳理 Reactor 的三个活跃实现区域。

| Directory | Responsibility / 职责 |
|---|---|
| [`reactor/core/`](reactor/core/README.md) | Canonical Python inference runtime / 标准 Python 推理运行时 |
| [`reactor/pro/`](reactor/pro/README.md) | Optional Pro serving extensions / 可选 Pro 服务扩展 |
| [`reactor/components/`](reactor/components/README.md) | Platform host-placement adapter / Platform 主机放置适配器 |

## Suggested reading order / 推荐阅读顺序

Read core first, then Pro extensions, and finally native components when low-level scheduling or transport is involved.

先阅读 core，再阅读 Pro 扩展；涉及底层调度或传输时，最后阅读原生组件。
