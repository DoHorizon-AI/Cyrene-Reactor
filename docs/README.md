# Reactor Documentation

Reactor 文档索引 / Documentation index for Reactor.

## Repository scope / 仓库范围

Reactor owns model inference and serving: engine admission, model loading, request scheduling, streaming, health, memory policy, and serving lifecycle. It consumes Platform contracts and replaceable engine capabilities.

Reactor 负责模型推理与服务：引擎准入、模型加载、请求调度、流式输出、健康检查、内存策略与服务生命周期。它消费 Platform 契约与可替换的引擎能力。

The runtime is split into a canonical Python core, optional Pro extensions, and Rust integrations. Generated protobuf bindings remain generated artifacts and are documented but not hand-edited.

运行时由标准 Python core、可选 Pro 扩展与 Rust 集成组成。生成的 protobuf 绑定属于生成制品，只做目录说明，不手工编辑。

## Reading map / 阅读地图

| Path | Responsibility / 职责 |
|---|---|
| [`architecture/overview.md`](architecture/overview.md) | Serving lifecycle, runtime topology, and ownership boundaries / 服务生命周期、运行时拓扑与职责边界 |
| [`architecture/tool-system.md`](architecture/tool-system.md) | Engine seam, bounded scheduling, residency, and placement boundaries / 引擎接缝、有界调度、驻留与放置边界 |
| [`architecture/mcp-integration.md`](architecture/mcp-integration.md) | Protocol adapter boundary and non-ownership rules / 协议适配边界与非归属规则 |
| [`modules/reactor/README.md`](modules/reactor/README.md) | Module map and recommended reading order / 模块地图与推荐阅读顺序 |
| [`glossary.md`](glossary.md) | Bilingual serving vocabulary / 双语服务术语 |
| [`faq.md`](faq.md) | Common questions and troubleshooting / 常见问题与排障指南 |
| [`API.md`](API.md) | Product/API contract and lifecycle state map / 产品 API 契约与生命周期状态图 |
| [`architecture-and-lifecycle.md`](architecture-and-lifecycle.md) | Existing as-is/to-be architecture and ownership notes / 现有架构、目标架构与归属说明 |
| [`REPOSITORY-LIFECYCLE.md`](REPOSITORY-LIFECYCLE.md) | Repository governance and release boundaries / 仓库治理与发布边界 |
| [`PUBLICATION.md`](PUBLICATION.md) | Public-source target, evidence boundary, and blockers / 公开源码目标、证据边界与阻塞项 |
| [`DEPENDENCY-LICENSES.md`](DEPENDENCY-LICENSES.md) | Direct dependency licenses and SBOM entrypoints / 直接依赖许可证与 SBOM 入口 |
| [`logging-and-errors.md`](logging-and-errors.md) | Cross-repository logging, error codes, and diagnostics specification / 跨仓日志、错误码与诊断规范 (草案 v0.1) |

## Suggested order / 推荐顺序

1. Read [`architecture/overview.md`](architecture/overview.md) for the serving lifecycle.
2. Read [`architecture/tool-system.md`](architecture/tool-system.md) for engine and resource ownership.
3. Read [`modules/reactor/README.md`](modules/reactor/README.md) to locate core, Pro, and native components.
4. Use [`API.md`](API.md), [`architecture-and-lifecycle.md`](architecture-and-lifecycle.md), [`glossary.md`](glossary.md), and [`faq.md`](faq.md) as references.

1. 先阅读 [`architecture/overview.md`](architecture/overview.md)，理解服务生命周期。
2. 再阅读 [`architecture/tool-system.md`](architecture/tool-system.md)，理解引擎与资源归属。
3. 阅读 [`modules/reactor/README.md`](modules/reactor/README.md)，定位 core、Pro 与原生组件。
4. 按需查阅 [`API.md`](API.md)、[`architecture-and-lifecycle.md`](architecture-and-lifecycle.md)、[`glossary.md`](glossary.md) 与 [`faq.md`](faq.md)。

## Change boundary / 变更边界

This publication pass changes only licenses, documentation, governance metadata,
and public-evidence hygiene. Environment-specific operational receipts are
excluded from the public candidate; runtime behavior, generated bindings,
dependency versions, and CI execution steps are unchanged.

本次公开发布准备只修改许可证、Markdown 文档、治理元数据与公开证据卫生；环境特定的运行
回执不进入公开候选，不改变运行时行为、生成绑定、依赖版本或 CI 执行步骤。
---
<!-- Chinese Translation / 中文翻译 -->

# Reactor 文档

Reactor 文档索引。

## 仓库范围

Reactor 负责模型推理和服务，包括引擎准入、模型加载、请求调度、流式输出、健康检查、内存策略和服务生命周期。它使用 Platform 契约和可替换的引擎能力。

运行时由规范 Python core、可选 Pro 扩展和 Rust 集成组成。生成的 protobuf 绑定属于生成产物，文档会说明其用途，但不会手工编辑。

## 阅读导航

| 路径 | 职责 |
|---|---|
| [`architecture/overview.md`](architecture/overview.md) | 服务生命周期、运行时拓扑和所有权边界 |
| [`architecture/tool-system.md`](architecture/tool-system.md) | 引擎接口、有界调度、驻留和放置边界 |
| [`architecture/mcp-integration.md`](architecture/mcp-integration.md) | 协议适配器边界与非归属规则 |
| [`modules/reactor/README.md`](modules/reactor/README.md) | 模块地图和建议阅读顺序 |
| [`glossary.md`](glossary.md) | 服务双语术语 |
| [`faq.md`](faq.md) | 常见问题与排障指南 |
| [`API.md`](API.md) | Product/API 契约与生命周期状态图 |
| [`architecture-and-lifecycle.md`](architecture-and-lifecycle.md) | 当前/目标架构和所有权说明 |
| [`REPOSITORY-LIFECYCLE.md`](REPOSITORY-LIFECYCLE.md) | 仓库治理与发布边界 |
| [`PUBLICATION.md`](PUBLICATION.md) | 公开源码目标、证据边界和阻塞项 |
| [`DEPENDENCY-LICENSES.md`](DEPENDENCY-LICENSES.md) | 直接依赖许可证与 SBOM 入口 |
| [`logging-and-errors.md`](logging-and-errors.md) | 跨仓日志、错误码和诊断规范（草案 v0.1） |

## 建议阅读顺序

1. 阅读 [`architecture/overview.md`](architecture/overview.md)，了解服务生命周期。
2. 阅读 [`architecture/tool-system.md`](architecture/tool-system.md)，了解引擎和资源所有权。
3. 阅读 [`modules/reactor/README.md`](modules/reactor/README.md)，定位 core、Pro 和原生组件。
4. 按需查阅 [`API.md`](API.md)、[`architecture-and-lifecycle.md`](architecture-and-lifecycle.md)、[`glossary.md`](glossary.md) 和 [`faq.md`](faq.md)。

## 变更边界

本次公开发布准备只修改许可证、文档、治理元数据和公开证据卫生。环境专属的运行回执不纳入公开候选；运行时行为、生成绑定、依赖版本和 CI 执行步骤均保持不变。
