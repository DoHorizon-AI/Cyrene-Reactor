# Reactor

Deployment and inference service for the Cyrene AI software matrix.

## Authoritative Documentation & Contracts
- **Product API & Serving Contract Specification**: [`docs/API.md`](docs/API.md)
- **Architecture & Serving Lifecycle**: [`docs/architecture-and-lifecycle.md`](docs/architecture-and-lifecycle.md)
- **Repository Architecture**: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Repository Lifecycle & Boundaries**: [`docs/REPOSITORY-LIFECYCLE.md`](docs/REPOSITORY-LIFECYCLE.md)
- **Plugin Dependencies**: [`PLUGIN_DEPENDENCIES.md`](PLUGIN_DEPENDENCIES.md)
- **Service Manifest**: [`service.json`](service.json)
- **Public-source publication note**: [`docs/PUBLICATION.md`](docs/PUBLICATION.md)
- **Dependency licenses and SBOM**: [`docs/DEPENDENCY-LICENSES.md`](docs/DEPENDENCY-LICENSES.md)
- **Security policy**: [`SECURITY.md`](SECURITY.md)
- **Contribution guide**: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- **License**: [`LICENSE`](LICENSE)

## Component Overview
Reactor runtime coordination is split from replaceable implementations:

- `runtime/core`: the Product-side inference coordinator, protocol bindings,
  scheduling, health, telemetry, and the fail-closed Direct Plugin adapter.
- `runtime/pro`: opt-in Product-side alerts and structured logging. It does not
  implement engines, caches, hardware discovery, or engine selection.
- `components/host-placement`: a thin adapter to Platform-owned placement; it
  neither implements placement policy nor allocates resources.

Concrete vLLM, TensorRT-LLM, Ascend/MindIE, remote-provider, model-analysis, and
compatibility algorithms live only in `Cyrene-Plugins-Official`.

Training code is owned by Yield and evaluation code is owned by Echo; neither is
duplicated here. Reactor has no optional GPU/NPU framework dependency, so its
Product checks remain runnable on CPU-only public CI. Real accelerator acceptance
belongs to the concrete engine packages in Cyrene-Plugins-Official.

This source snapshot is the content prepared for a clean-root public repository.
The former development history is retained only in a separate private archive;
the public repository must not inherit its branches, tags, pull-request refs,
or reflogs. The hosting visibility switch remains an explicit owner operation.
Check [`docs/PUBLICATION.md`](docs/PUBLICATION.md) for the remaining dependency,
license, and evidence gates.
