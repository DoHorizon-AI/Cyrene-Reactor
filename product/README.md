# Reactor Product / Reactor 产品

The Product package owns Deployment and Endpoint state, ArtifactRef admission,
serving-binding selection, restart/stop reconciliation, and the explicit Exchange
handoff. It does not inspect model weights or contain a vLLM, TensorRT-LLM,
MindIE, Transformers, or remote model-provider implementation.

产品包拥有 Deployment、Endpoint、ArtifactRef 准入、服务绑定选择、重启/停止协调以及显式
Exchange 交接；不检查模型权重，也不再实现 vLLM、TensorRT-LLM、MindIE、Transformers
或远程模型提供商。

## Runtime boundary / 运行时边界

Concrete engines live in `Cyrene-Plugins-Official` behind
`execution.engine.v1`. Platform owns generic package lifecycle and returns an
opaque local `connection_ref`; Reactor's runtime opens that endpoint directly
with the versioned `cyrene-plugin-runtime` SDK. Missing or failed bindings are
fail-closed and never select local engine code.

具体引擎位于 `Cyrene-Plugins-Official`，统一实现 `execution.engine.v1`。Platform
只管理通用包生命周期并返回不透明的本地 `connection_ref`；Reactor 通过版本化
`cyrene-plugin-runtime` SDK 直连。绑定缺失或失败时立即失败，不回退到本地实现。

The Product controller may consume an operator-admitted serving host through
`RemoteServingExecutionPort`; that adapter coordinates Product deployment state
and does not implement an inference algorithm. The removed Reactor-local CUDA
host/worker/bootstrap is no longer a supported production or CI path.

Product controller 可通过 `RemoteServingExecutionPort` 消费运维准入的服务主机；
该适配器只协调产品部署状态，不实现推理算法。原 Reactor 本地 CUDA host、worker 和
bootstrap 已从生产与 CI 路径移除。

## Run / 运行

Create the Product credential, then start the controller with an explicit
configuration containing `database_path`, `credential_file`,
`serving_bindings`, and `public_base_url`:

```bash
uv run cyrene-reactor init-secrets --config "$CYRENE_PRIVATE_CONFIG_DIR/reactor/credentials"
uv run cyrene-reactor control --config "$CYRENE_PRIVATE_CONFIG_DIR/reactor/control.json" --port 19300
```

Remote listeners require TLS. Credentials remain in private files and are never
exported in Deployment or Endpoint resources.

## Evidence limits / 证据边界

CPU unit and local DirectPluginRuntime tests prove contract wiring only. They do
not prove a real vLLM installation, GPU execution, hosted CI, deployment, merge,
or canonical read-back. Historical GPU evidence under `evidence/` describes the
removed Reactor-local worker and must not be reused as evidence for the new
Plugins-owned runtime.
---
<!-- Chinese Translation / 中文翻译 -->

# Reactor Product

Product 软件包负责 Deployment 和 Endpoint 状态、ArtifactRef 准入、服务绑定选择、重启/停止协调以及显式的 Exchange 交接。它不会检查模型权重，也不包含 vLLM、TensorRT-LLM、MindIE、Transformers 或远程模型提供方实现。

## 运行时边界

具体引擎位于 `Cyrene-Plugins-Official`，并通过 `execution.engine.v1` 提供能力。Platform 负责通用软件包生命周期并返回不透明的本地 `connection_ref`；Reactor 的运行时使用版本化 `cyrene-plugin-runtime` SDK 直接打开该端点。绑定缺失或失败时按失败即拒绝处理，绝不选择本地引擎代码。

Product controller 可以通过 `RemoteServingExecutionPort` 使用经过运维准入的服务主机。该适配器只协调 Product 部署状态，不实现推理算法。Reactor 本地 CUDA host、worker 和 bootstrap 已移除，不再是受支持的生产或 CI 路径。

## 运行

先创建 Product 凭据，再使用包含 `database_path`、`credential_file`、`serving_bindings` 和 `public_base_url` 的显式配置启动 controller：

```bash
uv run cyrene-reactor init-secrets --config "$CYRENE_PRIVATE_CONFIG_DIR/reactor/credentials"
uv run cyrene-reactor control --config "$CYRENE_PRIVATE_CONFIG_DIR/reactor/control.json" --port 19300
```

远程监听器必须使用 TLS。凭据应留在私有文件中，绝不能导出到 Deployment 或 Endpoint 资源。

## 证据范围

CPU 单元测试和本地 DirectPluginRuntime 测试只能证明契约接线，不能证明真实 vLLM 安装、GPU 执行、托管 CI、部署、合并或规范目标回读。`evidence/` 下的历史 GPU 证据描述的是已经移除的 Reactor 本地 worker，不能作为 Plugins 所有的新运行时证据。
