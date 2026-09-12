# runtime/core/src/cy_exec/core / runtime/core/src/cy_exec/core

Inference-server coordination, scheduling, memory, and telemetry.

推理服务协调、调度、内存与遥测。

## Files / 文件

| Entry | Responsibility / 职责 |
|---|---|
| `runtime/core/src/cy_exec/core/__init__.py` | Package initializer and public import boundary. / 包初始化与公开导入边界。 |
| `runtime/core/src/cy_exec/core/memory_manager.py` | Python runtime or test module: memory_manager.py. / Python 运行时或测试模块：memory_manager.py。 |
| `runtime/core/src/cy_exec/core/server.py` | Python runtime or test module: server.py. / Python 运行时或测试模块：server.py。 |
| `runtime/core/src/cy_exec/core/task_scheduler.py` | Python runtime or test module: task_scheduler.py. / Python 运行时或测试模块：task_scheduler.py。 |
| `runtime/core/src/cy_exec/core/telemetry.py` | Python runtime or test module: telemetry.py. / Python 运行时或测试模块：telemetry.py。 |

## Suggested reading order / 推荐阅读顺序

Start with `runtime/core/src/cy_exec/core/__init__.py` and then follow the module imports or package entry point.
Read sibling modules in the order required by the runtime path; consult parent and package READMEs for boundaries.
从 `runtime/core/src/cy_exec/core/__init__.py` 开始，再按模块导入关系或包入口继续阅读。
按运行时路径阅读同级模块；边界说明请查阅父目录和包 README。
