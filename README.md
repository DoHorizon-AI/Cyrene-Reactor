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
---
<!-- Chinese Translation / 中文翻译 -->

# Reactor

Cyrene AI 软件矩阵中的部署与推理服务。

## 权威文档与契约
- **Product API 与服务契约规范**：[`docs/API.md`](docs/API.md)
- **架构与服务生命周期**：[`docs/architecture-and-lifecycle.md`](docs/architecture-and-lifecycle.md)
- **仓库架构**：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- **仓库生命周期与边界**：[`docs/REPOSITORY-LIFECYCLE.md`](docs/REPOSITORY-LIFECYCLE.md)
- **Plugin 依赖**：[`PLUGIN_DEPENDENCIES.md`](PLUGIN_DEPENDENCIES.md)
- **服务清单**：[`service.json`](service.json)
- **公开源码发布说明**：[`docs/PUBLICATION.md`](docs/PUBLICATION.md)
- **依赖许可证与 SBOM**：[`docs/DEPENDENCY-LICENSES.md`](docs/DEPENDENCY-LICENSES.md)
- **安全策略**：[`SECURITY.md`](SECURITY.md)
- **贡献指南**：[`CONTRIBUTING.md`](CONTRIBUTING.md)
- **许可证**：[`LICENSE`](LICENSE)

## 组件概览
Reactor 的运行时协调与可替换实现彼此分离：

- `runtime/core`：Product 侧推理协调器、协议绑定、调度、健康检查、遥测，以及失败即拒绝的 Direct Plugin 适配器。
- `runtime/pro`：可选的 Product 侧告警和结构化日志；不实现引擎、缓存、硬件发现或引擎选择。
- `components/host-placement`：连接 Platform 所有放置能力的轻量适配器；不实现放置策略，也不分配资源。

具体的 vLLM、TensorRT-LLM、Ascend/MindIE、远程提供方、模型分析和兼容性算法只存在于 `Cyrene-Plugins-Official`。

训练代码由 Yield 负责，评估代码由 Echo 负责；两者都不会在此重复。Reactor 不依赖可选 GPU/NPU 框架，因此其 Product 检查可在纯 CPU 的公开 CI 上运行。真实加速器验收由 `Cyrene-Plugins-Official` 中的具体引擎软件包负责。

此源码快照是为干净根目录的公开仓库准备的内容。原开发历史仅保存在单独的私有归档中；公开仓库不得继承其分支、标签、拉取请求引用或 reflog。切换托管可见性仍须由 owner 明确操作。剩余依赖、许可证和证据门禁见 [`docs/PUBLICATION.md`](docs/PUBLICATION.md)。
