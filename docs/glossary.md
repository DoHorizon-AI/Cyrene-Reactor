# Glossary / 术语表

| English | 中文 | Meaning / 含义 |
|---|---|---|
| Reactor | Reactor 推理服务 | Cyrene product for model serving and inference / Cyrene 的模型服务与推理产品 |
| InferenceServer | 推理服务 | Coordinator for configuration, loading, serving, health, and shutdown / 负责配置、加载、服务、健康与关闭的协调器 |
| Serving engine | 服务引擎 | Concrete runtime that executes model inference / 执行模型推理的具体运行时 |
| Engine provider | 引擎提供方 | Capability implementation that creates a serving engine / 创建服务引擎的能力实现 |
| Engine factory | 引擎工厂 | Product-side callable that resolves one Plugins-owned execution provider / 解析一个 Plugins 所有执行提供方的 Product 侧可调用对象 |
| TaskScheduler | 任务调度器 | Bounded queue and worker execution coordinator / 有界队列与工作器执行协调器 |
| Admission control | 准入控制 | Policy deciding whether a request may enter serving / 决定请求是否进入服务的策略 |
| Backpressure | 背压 | Mechanism limiting work when capacity is exhausted / 容量耗尽时限制工作的机制 |
| Graceful draining | 优雅排空 | Stop accepting new work while completing in-flight work / 停止新任务并完成存量任务 |
| KV cache | KV 缓存 | Serving-time key/value attention state reused across tokens or requests / 在 token 或请求间复用的注意力键值状态 |
| Prompt cache | 提示缓存 | Reusable cache for prompt-prefix computation / 复用提示前缀计算的缓存 |
| `connection_ref` | 不透明连接引用 | Platform-resolved endpoint fact consumed by the Plugins-owned direct SDK / 由 Platform 解析并交给 Plugins 直连 SDK 的端点事实 |
| Sidecar | Sidecar 边车 | Native helper process adjacent to the Python runtime / 与 Python 运行时相邻的原生辅助进程 |
| Health probe | 健康探针 | Check that a worker can safely receive traffic / 检查工作器是否可以安全接收流量 |
| Fail-closed | 故障关闭 | Reject traffic when readiness or safety cannot be established / 无法确认就绪或安全时拒绝流量 |
| Generated binding | 生成绑定 | Protocol code produced from a schema and not hand-maintained / 由 schema 生成而非手工维护的协议代码 |
