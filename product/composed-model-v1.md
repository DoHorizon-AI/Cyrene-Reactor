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
