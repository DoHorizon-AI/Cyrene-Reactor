# Reactor Pro runtime / Reactor Pro 运行时

## Purpose / 目录用途

The optional Pro package extends the Product coordinator with alerts and structured logging.

可选 Pro 包在产品协调器之上提供告警与结构化日志。

## Files and responsibilities / 文件与职责

| Path | Responsibility / 职责 |
|---|---|
| [`../../../../runtime/pro/README.md`](../../../../runtime/pro/README.md) | Installation, package layout, and explicit limitations / 安装、包布局与明确限制 |
| `runtime/pro/src/cy_exec_pro/core/` | Product-side alerts / Product 侧告警 |
| `runtime/pro/src/cy_exec_pro/engines/` | Reserved namespace without implementations / 不含实现的保留命名空间 |
| `runtime/pro/src/cy_exec_pro/utils/` | Structured logging and shared utilities / 结构化日志与共享工具 |
| `runtime/pro/tests/` | Active Pro regression tests / 活跃 Pro 回归测试 |

## Suggested reading order / 推荐阅读顺序

1. `runtime/pro/README.md` — read installation and limitations first.
2. `core/alert_manager.py` — inspect Product alert policy.
3. `tests/` — verify the retained extension behavior.

1. 先阅读 `runtime/pro/README.md` 的安装与限制。
2. `core/alert_manager.py` —— 查看 Product 告警策略。
3. `tests/` —— 核对保留的扩展行为。
