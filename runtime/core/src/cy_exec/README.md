# runtime/core/src/cy_exec / runtime/core/src/cy_exec

Canonical inference worker package.

标准推理工作器包。

## Files / 文件

| Entry | Responsibility / 职责 |
|---|---|
| `runtime/core/src/cy_exec/config/` | Product model bindings and selected Plugin identity / Product 模型绑定与所选插件身份 |
| `runtime/core/src/cy_exec/core/` | Inference coordination, bounded scheduling, model residency, and request telemetry / 推理协调、有界调度、模型驻留与请求遥测 |
| `runtime/core/src/cy_exec/engines/` | Consumer-side engine port only / 仅消费侧引擎端口 |
| `runtime/core/src/cy_exec/health/` | Health and readiness HTTP endpoints. / 健康与就绪 HTTP 端点。 |
| `runtime/core/src/cy_exec/proto/` | Generated protocol bindings and package boundary. / 生成的协议绑定与包边界。 |
| `runtime/core/src/cy_exec/utils/` | Transport authentication, TLS, tracing, paths, and stream helpers / 传输认证、TLS、追踪、路径与流辅助函数 |
| `runtime/core/src/cy_exec/__init__.py` | Package initializer and public import boundary. / 包初始化与公开导入边界。 |
| `runtime/core/src/cy_exec/capability_seam.py` | Python runtime or test module: capability_seam.py. / Python 运行时或测试模块：capability_seam.py。 |
| `runtime/core/src/cy_exec/constants.py` | Python runtime or test module: constants.py. / Python 运行时或测试模块：constants.py。 |
| `runtime/core/src/cy_exec/exceptions.py` | Python runtime or test module: exceptions.py. / Python 运行时或测试模块：exceptions.py。 |
| `runtime/core/src/cy_exec/grpc_servicer.py` | Python runtime or test module: grpc_servicer.py. / Python 运行时或测试模块：grpc_servicer.py。 |
| `runtime/core/src/cy_exec/grpc_servicer_async.py` | Python runtime or test module: grpc_servicer_async.py. / Python 运行时或测试模块：grpc_servicer_async.py。 |
| `runtime/core/src/cy_exec/main.py` | Python runtime or test module: main.py. / Python 运行时或测试模块：main.py。 |

## Suggested reading order / 推荐阅读顺序

Start with `runtime/core/src/cy_exec/core/server.py` and then follow the module imports or package entry point.
Read sibling modules in the order required by the runtime path; consult parent and package READMEs for boundaries.
从 `runtime/core/src/cy_exec/core/server.py` 开始，再按模块导入关系或包入口继续阅读。
按运行时路径阅读同级模块；边界说明请查阅父目录和包 README。
