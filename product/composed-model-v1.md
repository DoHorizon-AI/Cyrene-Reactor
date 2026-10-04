# Reactor composed model V1

Reactor consumes the Yield `ModelVersion` SDK as the only canonical model
identity authority. A legacy request containing only `modelArtifact` is
normalized to `FULL_MODEL`. A composed request must contain an explicit
`BASE_PLUS_LORA` ModelVersion and carries its `modelVersion.id` through the
Deployment, selected Plugin request, runtime readback, and Exchange handoff.

`BASE_PLUS_LORA` contains one portable base model ArtifactRef and one portable
adapter ArtifactRef. Both references use `kind=model` and
`manifest_digest=digest`; the adapter role is selected by the ModelVersion
composition. Reactor never copies PEFT rank, alpha, or target modules into the
ModelVersion. Those values remain in `adapter_config.json`.

Platform staging verifies CAS digest and file integrity. Product validates only
the canonical `ModelVersion` and ArtifactRef projections. Model structure,
adapter compatibility, supported PEFT features, tensor shapes, and concrete
LoRA loading are Plugins-owned behavior. The vLLM Plugin receives the base and
adapter paths through the versioned `execution.engine.v1` contract and fails
closed if its runtime cannot load that composition.

Tokenizer and chat-template overrides remain ArtifactRefs. Product preserves
their identity but does not parse or rewrite provider-specific contents;
support and compatibility are decided by the selected Plugin. Inheritance
remains the default. A future
merge/export operation creates a new
`FULL_MODEL` ModelVersion with `derivedFromModelVersion`; it never mutates the
composed identity.
Yield handoff provides the canonical base reference, adapter ArtifactRef,
optional tokenizer/template overrides, and TrainingRun/DatasetVersion lineage.
Reactor validates that document through the pinned Yield contract package.
---
<!-- Chinese Translation / 中文翻译 -->

# Reactor 组合模型 V1

Reactor 仅使用 Yield 的 `ModelVersion` SDK 作为规范模型标识权威。只包含旧版 `modelArtifact` 的请求会规范化为 `FULL_MODEL`。组合模型请求必须明确提供 `BASE_PLUS_LORA` ModelVersion，并在 Deployment、选定的 Plugin 请求、运行时回读和 Exchange 交接过程中持续携带 `modelVersion.id`。

`BASE_PLUS_LORA` 包含一个可移植的基础模型 ArtifactRef 和一个可移植的适配器 ArtifactRef。两个引用都使用 `kind=model` 和 `manifest_digest=digest`；适配器角色由 ModelVersion 组合定义。Reactor 不会把 PEFT rank、alpha 或 target modules 复制到 ModelVersion；这些值仍保存在 `adapter_config.json` 中。

Platform 暂存过程会验证 CAS 摘要和文件完整性。Product 只验证规范的 `ModelVersion` 和 ArtifactRef 投影。模型结构、适配器兼容性、支持的 PEFT 功能、张量形状以及具体 LoRA 加载行为均由 Plugins 负责。vLLM Plugin 通过有版本的 `execution.engine.v1` 契约接收基础模型和适配器路径；若运行时无法加载该组合，则按失败即拒绝处理。

Tokenizer 和聊天模板覆盖项仍以 ArtifactRef 表示。Product 保留它们的标识，但不解析或改写提供方专属内容；是否支持及是否兼容由选定的 Plugin 决定。默认仍采用继承。未来的合并/导出操作会创建新的 `FULL_MODEL` ModelVersion，并设置 `derivedFromModelVersion`；不会修改组合模型标识。

Yield 交接提供规范基础模型引用、适配器 ArtifactRef、可选 tokenizer/模板覆盖项，以及 TrainingRun/DatasetVersion 血缘信息。Reactor 使用固定版本的 Yield 契约软件包验证该文档。
