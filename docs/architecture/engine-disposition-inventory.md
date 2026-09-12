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
