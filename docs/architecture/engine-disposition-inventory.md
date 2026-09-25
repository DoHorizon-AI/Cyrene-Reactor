# Reactor engine disposition inventory (REA-002)

This ledger records the completed local source cutover. It is not hosted, GPU,
merge, or canonical read-back evidence.

| Surface | Disposition | Current state |
|---|---|---|
| `runtime/core/src/cy_exec/engines/abstract_engine.py` | `SUPPORT` | Product-side port type only. |
| `runtime/core/src/cy_exec/engines/{engine_factory,vllm_*,trt_engine,mindie_engine,nvidia_engine,ascend_engine}.py` | `REMOVE` | Deleted; no Product concrete engine factory remains. |
| `runtime/pro/src/cy_exec_pro/core/{engine_selector,hardware_detector,config_injector}.py` | `REMOVE` | Deleted; engine choice is Plugins-owned and hardware facts are Platform-owned. |
| `runtime/pro/src/cy_exec_pro/engines/api_engine.py` | `REMOVE` | Deleted; provider relay implementations belong in Plugins. |
| `product/src/cyrene_reactor_product/{host_api,host_runtime,installation,kernel_rpc,vllm_worker}.py` | `REMOVE` | Deleted Reactor-local CUDA worker/bootstrap path. |
| `product/src/cyrene_reactor_product/{reference_server.py,ProcessServingExecutionPort}` | `REMOVE` | Deleted the production-packaged reference serving implementation; Product tests use a test-only lifecycle double. |
| `product/src/cyrene_reactor_product/model_package.py` | `REMOVE` | Deleted unreachable model/safetensors/LoRA analysis logic; model analysis and execution compatibility remain Plugins-owned while artifact identity/integrity remains Platform-owned. |
| `serving-runtime/` | `REMOVE` | Deleted Reactor-local vLLM environment/bootstrap bundle. |
| Root optional `nvidia`/`vllm` dependencies | `REMOVE` | Deleted; Service CI no longer installs concrete engine frameworks. |
| `runtime/core/src/cy_exec/capability_seam.py` | `SUPPORT` | DirectPluginRuntime adapter; missing or invalid bindings fail closed. |
| `Cyrene-Plugins-Official/plugins/engines/*` | `MOVE` | Canonical vLLM, TensorRT-LLM, and MindIE implementations; vLLM owns LoRA execution. |

The only production profile is `DIRECT_PLUGIN`. Platform may resolve and
supervise a package, but model load/inference payloads travel directly between
Reactor and the Plugins-owned endpoint.
---
<!-- Chinese Translation / 中文翻译 -->

# Reactor 引擎处置清单（REA-002）

本台账记录已完成的本地源码切换，不代表托管 CI、GPU、合并或规范目标回读证据。

| 接口/路径 | 处置 | 当前状态 |
|---|---|---|
| `runtime/core/src/cy_exec/engines/abstract_engine.py` | `SUPPORT` | 仅保留 Product 侧端口类型。 |
| `runtime/core/src/cy_exec/engines/{engine_factory,vllm_*,trt_engine,mindie_engine,nvidia_engine,ascend_engine}.py` | `REMOVE` | 已删除；Product 不再保留具体引擎工厂。 |
| `runtime/pro/src/cy_exec_pro/core/{engine_selector,hardware_detector,config_injector}.py` | `REMOVE` | 已删除；引擎选择由 Plugins 负责，硬件事实由 Platform 负责。 |
| `runtime/pro/src/cy_exec_pro/engines/api_engine.py` | `REMOVE` | 已删除；提供方中继实现归 Plugins 所有。 |
| `product/src/cyrene_reactor_product/{host_api,host_runtime,installation,kernel_rpc,vllm_worker}.py` | `REMOVE` | 已删除 Reactor 本地 CUDA 工作进程/引导路径。 |
| `product/src/cyrene_reactor_product/{reference_server.py,ProcessServingExecutionPort}` | `REMOVE` | 已删除随生产包发布的参考服务实现；Product 测试使用仅用于测试的生命周期替身。 |
| `product/src/cyrene_reactor_product/model_package.py` | `REMOVE` | 已删除不可达的模型/safetensors/LoRA 分析逻辑；模型分析和执行兼容性由 Plugins 负责，Artifact 标识/完整性仍由 Platform 负责。 |
| `serving-runtime/` | `REMOVE` | 已删除 Reactor 本地 vLLM 环境/引导组件。 |
| 根级可选 `nvidia`/`vllm` 依赖 | `REMOVE` | 已删除；Service CI 不再安装具体引擎框架。 |
| `runtime/core/src/cy_exec/capability_seam.py` | `SUPPORT` | DirectPluginRuntime 适配器；绑定缺失或无效时按失败即拒绝处理。 |
| `Cyrene-Plugins-Official/plugins/engines/*` | `MOVE` | 规范的 vLLM、TensorRT-LLM 和 MindIE 实现；LoRA 执行由 vLLM 负责。 |

唯一的生产配置是 `DIRECT_PLUGIN`。Platform 可以解析并监管软件包，但模型加载/推理载荷会在 Reactor 与 Plugins 所有的端点之间直接传输。
