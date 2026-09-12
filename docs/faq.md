# FAQ and troubleshooting / 常见问题与排障

## Which runtime is canonical? / 哪个运行时是标准实现？

`runtime/core/src/cy_exec` is the canonical community inference runtime. `runtime/pro` is optional and must be installed explicitly; Rust components provide native integrations.

`runtime/core/src/cy_exec` 是标准社区推理运行时。`runtime/pro` 是可选扩展，必须显式安装；Rust 组件提供原生集成。

## Why are some protocol files not edited? / 为什么不编辑部分协议文件？

The files under `runtime/core/src/cy_exec/proto` are generated bindings. Change the source contract and regenerate them through the repository tooling; do not hand-edit generated output as part of a comment-only task.

`runtime/core/src/cy_exec/proto` 下的文件是生成绑定。应修改源契约并通过仓库工具重新生成；注释补全任务不手工编辑生成输出。

## What is the serving lifecycle? / 服务生命周期是什么？

Follow `CREATED → CONFIGURED → LOADING → READY → SERVING → DRAINING → STOPPED`. Load failures must release engine resources, readiness must fail closed, and draining must reject new work.

生命周期为 `CREATED → CONFIGURED → LOADING → READY → SERVING → DRAINING → STOPPED`。加载失败必须释放引擎资源，就绪检查必须故障关闭，排空阶段必须拒绝新任务。

## Who owns hardware facts and memory policy? / 谁负责硬件事实与内存策略？

Platform Node Agent owns canonical hardware facts and Platform owns generic resource leases. Reactor owns serving admission, bounded queueing, and loaded-model residency/eviction policy using reported observations. Engine Plugins own concrete KV allocation and memory-pool behavior; gateway cache Plugins own prompt/response caching.

Platform Node Agent 负责标准硬件事实，Platform 负责通用资源租约。Reactor 负责服务准入、有界排队以及基于上报事实的模型驻留/驱逐策略；引擎插件负责具体 KV 分配与内存池，网关缓存插件负责 Prompt/响应缓存。

## Why does a CPU-only import work while inference does not? / 为什么 CPU 环境能导入但不能推理？

Optional GPU/NPU dependencies are intentionally lazy. Import and compile checks can run without accelerators, but a selected engine still requires its runtime, device, model, and compatible driver dependencies at execution time.

GPU/NPU 可选依赖被有意延迟导入。没有加速卡也可以执行导入与编译检查，但实际选定引擎仍需要对应运行时、设备、模型与兼容驱动依赖。

## How should a serving failure be isolated? / 如何定位服务失败？

Check in order: configuration validation, model artifact availability, engine selection, weight loading, readiness, queue admission, engine execution, stream transport, and cleanup. Keep provider, scheduler, and lifecycle errors distinct.

按以下顺序排查：配置校验、模型制品可用性、引擎选择、权重加载、就绪状态、队列准入、引擎执行、流传输与清理。将提供方、调度器与生命周期错误分开。

## What should not be added to Reactor? / Reactor 不应加入什么？

Do not add training, evaluation, public gateway authentication, or canonical node hardware probing. Those responsibilities belong to Yield, Echo, Exchange, and Platform Node Agent respectively.

不要在 Reactor 中加入训练、评估、公共网关认证或标准节点硬件探测；这些职责分别归属于 Yield、Echo、Exchange 与 Platform Node Agent。

## How should an MCP adapter be reviewed? / 如何评审 MCP 适配器？

Treat MCP as transport. Reuse serving admission, timeout, cancellation, health, capability resolution, and secret-redaction policies; never expose arbitrary process, filesystem, or engine-internal controls.

将 MCP 视为传输层。复用服务准入、超时、取消、健康、能力解析与密钥脱敏策略；绝不暴露任意进程、文件系统或引擎内部控制。
