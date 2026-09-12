# runtime/core/tests / runtime/core/tests

Active core-runtime tests.

核心运行时活跃测试。

## Files / 文件

| Entry | Responsibility / 职责 |
|---|---|
| `runtime/core/tests/__init__.py` | Package initializer and public import boundary. / 包初始化与公开导入边界。 |
| `runtime/core/tests/test_abstract_engine.py` | Python runtime or test module: test_abstract_engine.py. / Python 运行时或测试模块：test_abstract_engine.py。 |
| `runtime/core/tests/test_auth.py` | Python runtime or test module: test_auth.py. / Python 运行时或测试模块：test_auth.py。 |
| `runtime/core/tests/test_capability_seam.py` | Python runtime or test module: test_capability_seam.py. / Python 运行时或测试模块：test_capability_seam.py。 |
| `runtime/core/tests/test_config_loader.py` | Python runtime or test module: test_config_loader.py. / Python 运行时或测试模块：test_config_loader.py。 |
| `runtime/core/tests/test_constants.py` | Python runtime or test module: test_constants.py. / Python 运行时或测试模块：test_constants.py。 |
| `runtime/core/tests/test_exceptions.py` | Python runtime or test module: test_exceptions.py. / Python 运行时或测试模块：test_exceptions.py。 |
| `runtime/core/tests/test_grpc_servicer.py` | Python runtime or test module: test_grpc_servicer.py. / Python 运行时或测试模块：test_grpc_servicer.py。 |
| `runtime/core/tests/test_health_server.py` | Python runtime or test module: test_health_server.py. / Python 运行时或测试模块：test_health_server.py。 |
| `runtime/core/tests/test_main.py` | Python runtime or test module: test_main.py. / Python 运行时或测试模块：test_main.py。 |
| `runtime/core/tests/test_memory_manager.py` | Python runtime or test module: test_memory_manager.py. / Python 运行时或测试模块：test_memory_manager.py。 |
| `runtime/core/tests/test_path_utils.py` | Python runtime or test module: test_path_utils.py. / Python 运行时或测试模块：test_path_utils.py。 |
| `runtime/core/tests/test_proto_roundtrip.py` | Python runtime or test module: test_proto_roundtrip.py. / Python 运行时或测试模块：test_proto_roundtrip.py。 |
| `runtime/core/tests/test_server.py` | Python runtime or test module: test_server.py. / Python 运行时或测试模块：test_server.py。 |
| `runtime/core/tests/test_stream_buffer.py` | Python runtime or test module: test_stream_buffer.py. / Python 运行时或测试模块：test_stream_buffer.py。 |
| `runtime/core/tests/test_task_scheduler.py` | Python runtime or test module: test_task_scheduler.py. / Python 运行时或测试模块：test_task_scheduler.py。 |
| `runtime/core/tests/test_telemetry.py` | Python runtime or test module: test_telemetry.py. / Python 运行时或测试模块：test_telemetry.py。 |

## Suggested reading order / 推荐阅读顺序

Start with `test_capability_seam.py`, then follow the Product coordination tests.
Read sibling modules in the order required by the runtime path; consult parent and package READMEs for boundaries.
从 `test_capability_seam.py` 开始，再阅读 Product 协调测试。
按运行时路径阅读同级模块；边界说明请查阅父目录和包 README。
