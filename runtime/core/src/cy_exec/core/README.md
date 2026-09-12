# runtime/core/src/cy_exec/core / runtime/core/src/cy_exec/core

Inference-server coordination, bounded scheduling, model residency, and request telemetry.

推理服务协调、有界调度、模型驻留与请求遥测。

## Files / 文件

| Entry | Responsibility / 职责 |
|---|---|
| `runtime/core/src/cy_exec/core/__init__.py` | Package initializer and public import boundary. / 包初始化与公开导入边界。 |
| `runtime/core/src/cy_exec/core/memory_manager.py` | Per-server loaded-model registry and Plugin memory observations / 每个服务实例的已加载模型注册表与插件内存观测 |
| `runtime/core/src/cy_exec/core/server.py` | Python runtime or test module: server.py. / Python 运行时或测试模块：server.py。 |
| `runtime/core/src/cy_exec/core/task_scheduler.py` | Python runtime or test module: task_scheduler.py. / Python 运行时或测试模块：task_scheduler.py。 |
| `runtime/core/src/cy_exec/core/telemetry.py` | Request, failure, latency, and token metrics / 请求、失败、延迟与 token 指标 |

## Suggested reading order / 推荐阅读顺序

Start with `runtime/core/src/cy_exec/core/__init__.py` and then follow the module imports or package entry point.
Read sibling modules in the order required by the runtime path; consult parent and package READMEs for boundaries.
从 `runtime/core/src/cy_exec/core/__init__.py` 开始，再按模块导入关系或包入口继续阅读。
按运行时路径阅读同级模块；边界说明请查阅父目录和包 README。
