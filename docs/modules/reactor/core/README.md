# Reactor core runtime / Reactor 核心运行时

## Purpose / 目录用途

The core runtime is the canonical `cy_exec` Product worker. It owns the consumer-side engine port, request scheduling, model binding configuration, health, protocol service, and telemetry coordination. Concrete engines live only in Cyrene-Plugins-Official.

核心运行时是标准的 `cy_exec` Product 工作器。它负责消费侧引擎端口、请求调度、模型绑定配置、健康检查、协议服务与遥测协调；具体引擎只存在于 Cyrene-Plugins-Official。

## Files and responsibilities / 文件与职责

| Path | Responsibility / 职责 |
|---|---|
| [`../../../../runtime/core/README.md`](../../../../runtime/core/README.md) | Package-level installation and generated-binding notes / 包级安装与生成绑定说明 |
| `runtime/core/src/cy_exec/` | Runtime package and public worker surface / 运行时包与公开工作器边界 |
| `runtime/core/src/cy_exec/engines/` | Consumer-side engine port only / 仅消费侧引擎端口 |
| `runtime/core/src/cy_exec/core/` | Server, scheduler, memory, and telemetry / 服务、调度器、内存与遥测 |
| `runtime/core/src/cy_exec/config/` | Configuration loading and validation / 配置加载与校验 |
| `runtime/core/src/cy_exec/health/` | Health/readiness server / 健康与就绪服务 |
| `runtime/core/src/cy_exec/proto/` | Generated protocol bindings / 生成的协议绑定 |
| `runtime/core/tests/` | Active runtime regression tests / 活跃运行时回归测试 |

## Suggested reading order / 推荐阅读顺序

1. `cy_exec/capability_seam.py` — understand serving capability contracts.
2. `cy_exec/core/server.py` — follow Product scheduling and lifecycle coordination.
3. `cy_exec/core/server.py` and `core/task_scheduler.py` — follow request execution.
4. `cy_exec/health/health_server.py` — inspect health boundaries.
5. `tests/` — verify the active behavior coverage.

1. `cy_exec/capability_seam.py` —— 理解服务能力契约。
2. `cy_exec/core/server.py` —— 跟踪 Product 调度与生命周期协调。
3. `cy_exec/core/server.py` 与 `core/task_scheduler.py` —— 跟踪请求执行。
4. `cy_exec/health/health_server.py` —— 查看健康边界。
5. `tests/` —— 核对活跃行为覆盖。
