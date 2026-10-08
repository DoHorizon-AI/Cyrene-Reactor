# Dependency licenses and SBOM entrypoints / 依赖许可证与 SBOM 入口

This inventory is derived from the checked-in manifests and lockfiles. It
describes dependencies resolved by the current Reactor source tree; it does
not grant a license to upstream code and does not replace the upstream license
files.

本清单根据当前提交中的 manifest 与锁文件生成，描述 Reactor 源码树解析到的依赖；
它不向上游代码授予许可证，也不替代上游许可证文件。

## First-party license / 本项目许可证

Reactor's own source, documentation, schemas, and generated Product contract
files are offered under the Apache License 2.0 in the repository root
[`LICENSE`](../LICENSE). A package's dependency licenses remain separate.

Reactor 自有源码、文档、schema 与生成的产品契约文件依据仓库根目录的
[`LICENSE`](../LICENSE) 以 Apache License 2.0 提供。依赖包的许可证仍然独立适用。

## Direct Python dependencies / Python 直接依赖

The versions below are the versions resolved by the current lockfiles. The
license expressions for registry packages were checked from their installed
metadata; the lockfiles remain the reproducible version source.

以下版本是当前锁文件解析出的版本。registry 包的许可证表达式已根据安装元数据核对；
锁文件仍是可复现版本的权威来源。

### Runtime and Product / 运行时与产品层

| Package | Version or revision | SPDX license | Source / note |
| --- | --- | --- | --- |
| `cyrene-plugin-runtime` | `0.2.0`, Plugins `3afbac4d386eb7a27f6778149187884820c0b7f6` | **UNDECLARED** | Plugins-owned direct transport SDK; its manifest currently has no license field, so public dependency closure is blocked until upstream metadata is corrected. |
| `grpcio` | `1.83.0` | `Apache-2.0` | PyPI runtime and generated transport support. |
| `grpcio-tools` | `1.83.0` | `Apache-2.0` | PyPI build-time protobuf tooling. |
| `protobuf` | `7.36.0` | `BSD-3-Clause` | PyPI runtime and generated message support. |
| `pydantic` | `2.13.4` (runtime), `2.13.5` (Product) | `MIT` | PyPI validation and settings models. |
| `pydantic-settings` | `2.15.0` | `MIT` | PyPI settings loading. |
| `PyYAML` | `6.0.3` | `MIT` | PyPI YAML parsing. |
| `packaging` | `26.3` | `Apache-2.0 OR BSD-2-Clause` | PyPI version and requirement parsing. |
| `watchdog` | `6.0.0` | `Apache-2.0` | PyPI file-watch support. |
| `fastapi` | `0.141.1` | `MIT` | Product HTTP API. |
| `httpx` | `0.28.1` | `BSD-3-Clause` | Product HTTP client and tests. |
| `uvicorn` | `0.52.4` | `BSD-3-Clause` | Product ASGI server. |
| `cyrene-artifacts` | `0.1.0`, Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform-owned ArtifactRef SDK; exact git revision is locked in `product/uv.lock`. |
| `cyrene-yield-contracts` | `0.1.0`, Yield `6fea8f835ce2561aaed4b0d9996856f6a3ef1ee6` | `Apache-2.0` | Yield-owned contract SDK; exact git revision is locked in `product/uv.lock`. |

### Development-only / 仅开发环境

| Package | Version | SPDX license | Use |
| --- | --- | --- | --- |
| `pytest` | `9.1.1` | `MIT` | Test runner. |
| `hypothesis` | `6.165.10` | `MPL-2.0` | Property-based tests. |
| `ruff` | `0.16.5` | `MIT` | Lint and formatting. |
| `jsonschema` | `4.26.0` | `MIT` | Product schema checks. |
| `mypy` | `2.3.1` | `MIT` | Product type checking. |
| `openapi-spec-validator` | `0.9.0` | `Apache-2.0` | OpenAPI validation. |

## Direct Rust dependencies / Rust 直接依赖

The `cyrene-reactor-host-placement` package and all of its resolved Platform
contract/placement dependencies are Apache-2.0. The component performs its
strict protobuf projection locally and does not link Platform's AGPL
`cy-adapter-client` IPC implementation.

`cyrene-reactor-host-placement` 包及其解析到的 Platform contract/placement 依赖均为
Apache-2.0。该组件在本地执行严格 protobuf 投影，不链接 Platform 的 AGPL
`cy-adapter-client` IPC 实现。

| Package | Revision or version | SPDX license | Source / note |
| --- | --- | --- | --- |
| `cy-execution-fabric` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform execution attachment contract. |
| `cy-kernel-contract` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform contract crate. |
| `cy-manifest` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform manifest crate. |
| `cy-proto` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform generated protocol crate. |
| `anyhow` | `1.0.104` | `MIT OR Apache-2.0` | Registry error context. |
| `prost` | `0.12.x` | `Apache-2.0` | Registry protobuf support. |
| `serde`, `serde_json` | locked in `Cargo.lock` | `MIT OR Apache-2.0` | Registry serialization support. |

The complete Rust transitive graph, checksums, and git revisions are in
[`Cargo.lock`](../Cargo.lock). Registry packages not repeated in this table
must retain the license metadata shipped by their upstream package.

完整 Rust 传递依赖图、校验和与 git revision 位于 [`Cargo.lock`](../Cargo.lock)。本表未
重复列出的 registry 包，仍必须保留其上游包附带的许可证元数据。

## Selected but not included / 选择但未包含的实现

vLLM and KServe are discussed in the architecture and evidence documents as
replaceable or future candidates. They are not dependencies of the current
lockfiles, and no vLLM or KServe source is copied into this repository. Their
licenses become relevant only when a distribution actually bundles them.

架构与证据文档中提到的 vLLM 与 KServe 是可替换或未来候选实现，不是当前锁文件依赖，
本仓库也没有复制其源码。只有发行版实际捆绑它们时，才需纳入对应许可证审查。

## SBOM entrypoints / SBOM 入口

Run these commands from a clean checkout to produce machine-readable inputs
for a CycloneDX or SPDX release report. The commands read the checked-in lock
files and write outside the repository so generated reports are not confused
with source evidence:

在干净检出中运行以下命令，可为 CycloneDX 或 SPDX 发布报告生成机器可读输入。命令读取
已提交的锁文件并将输出写到仓库外，避免把生成报告混同于源码证据：

```bash
sbom_dir="$(mktemp -d)"

# Root runtime and development graph
uv export --frozen --all-groups --format cyclonedx1.5 \
  --output-file "$sbom_dir/cyrene-reactor-runtime.cdx.json"

# Product graph
(cd product && uv export --frozen --all-groups --format cyclonedx1.5 \
  --output-file "$sbom_dir/cyrene-reactor-product.cdx.json")

# Rust graph with checksums and exact git revisions
cargo metadata --locked --format-version 1 \
  > "$sbom_dir/cyrene-reactor-rust-metadata.json"
```

Before a public source or binary release, the generated report must be
reviewed for `UNDECLARED` licenses and any
new git dependency. A successful local export is not a legal approval.

公开源码或二进制发布前，必须审查生成报告中的 `UNDECLARED` 许可证与新增 git 依赖。
本地导出成功不等于法律批准。
---
<!-- Chinese Translation / 中文翻译 -->

# 依赖许可证与 SBOM 入口

本清单根据检入仓库的 manifests 和锁文件生成，描述当前 Reactor 源码树解析到的依赖。它不会向上游代码授予许可证，也不能替代上游许可证文件。

## 本项目许可证

Reactor 自有源码、文档、架构和生成的 Product 契约文件依据 Apache License 2.0 提供，见仓库根目录 [`LICENSE`](../LICENSE)。软件包依赖的许可证单独适用。

## Python 直接依赖

以下版本是当前锁文件解析出的版本。registry 软件包的许可证表达式已根据安装元数据核对；可复现版本仍以锁文件为准。

### 运行时与 Product

| 软件包 | 版本或修订 | SPDX 许可证 | 来源 / 说明 |
|---|---|---|---|
| `cyrene-plugin-runtime` | `0.2.0`，Plugins `3afbac4d386eb7a27f6778149187884820c0b7f6` | **未声明** | Plugins 所有的直连传输 SDK；其 manifest 目前没有许可证字段，因此在上游修正元数据之前，公开依赖闭包受阻。 |
| `grpcio` | `1.83.0` | `Apache-2.0` | PyPI 运行时和生成传输支持。 |
| `grpcio-tools` | `1.83.0` | `Apache-2.0` | PyPI 构建时 protobuf 工具。 |
| `protobuf` | `7.36.0` | `BSD-3-Clause` | PyPI 运行时和生成消息支持。 |
| `pydantic` | `2.13.4`（运行时），`2.13.5`（Product） | `MIT` | PyPI 验证和设置模型。 |
| `pydantic-settings` | `2.15.0` | `MIT` | PyPI 设置加载。 |
| `PyYAML` | `6.0.3` | `MIT` | PyPI YAML 解析。 |
| `packaging` | `26.3` | `Apache-2.0 OR BSD-2-Clause` | PyPI 版本和依赖要求解析。 |
| `watchdog` | `6.0.0` | `Apache-2.0` | PyPI 文件监视支持。 |
| `fastapi` | `0.141.1` | `MIT` | Product HTTP API。 |
| `httpx` | `0.28.1` | `BSD-3-Clause` | Product HTTP 客户端和测试。 |
| `uvicorn` | `0.52.4` | `BSD-3-Clause` | Product ASGI 服务器。 |
| `cyrene-artifacts` | `0.1.0`，Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform 所有的 ArtifactRef SDK；精确 git 修订锁定在 `product/uv.lock`。 |
| `cyrene-yield-contracts` | `0.1.0`，Yield `6fea8f835ce2561aaed4b0d9996856f6a3ef1ee6` | `Apache-2.0` | Yield 所有的契约 SDK；精确 git 修订锁定在 `product/uv.lock`。 |

### 仅开发依赖

| 软件包 | 版本 | SPDX 许可证 | 用途 |
|---|---|---|---|
| `pytest` | `9.1.1` | `MIT` | 测试运行器。 |
| `hypothesis` | `6.165.10` | `MPL-2.0` | 基于属性的测试。 |
| `ruff` | `0.16.5` | `MIT` | lint 和格式化。 |
| `jsonschema` | `4.26.0` | `MIT` | Product 架构检查。 |
| `mypy` | `2.3.1` | `MIT` | Product 类型检查。 |
| `openapi-spec-validator` | `0.9.0` | `Apache-2.0` | OpenAPI 验证。 |

## Rust 直接依赖

`cyrene-reactor-host-placement` 软件包及其解析到的全部 Platform 契约/放置依赖均为 Apache-2.0。该组件在本地执行严格的 protobuf 投影，不链接 Platform 的 AGPL `cy-adapter-client` IPC 实现。

| 软件包 | 修订或版本 | SPDX 许可证 | 来源 / 说明 |
|---|---|---|---|
| `cy-execution-fabric` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform 执行附件契约。 |
| `cy-kernel-contract` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform 契约 crate。 |
| `cy-manifest` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform manifest crate。 |
| `cy-proto` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform 生成协议 crate。 |
| `anyhow` | `1.0.104` | `MIT OR Apache-2.0` | registry 错误上下文。 |
| `prost` | `0.12.x` | `Apache-2.0` | registry protobuf 支持。 |
| `serde`、`serde_json` | 由 `Cargo.lock` 固定 | `MIT OR Apache-2.0` | registry 序列化支持。 |

完整 Rust 传递依赖图、校验和及 git 修订位于 [`Cargo.lock`](../Cargo.lock)。此表未重复列出的 registry 软件包仍必须保留其上游软件包附带的许可证元数据。

## 已选择但未纳入的实现

架构和证据文档将 vLLM 与 KServe 列为可替换或未来候选。它们不是当前锁文件依赖，本仓库也没有复制其源码。只有实际发行版捆绑了它们时，才需要审查其许可证。

## SBOM 入口

在干净检出目录运行以下命令，可为 CycloneDX 或 SPDX 发布报告生成机器可读输入。命令读取检入仓库的锁文件，并将结果写入仓库外，避免把生成报告误认为源码证据：

```bash
sbom_dir="$(mktemp -d)"

# 根运行时和开发依赖图
uv export --frozen --all-groups --format cyclonedx1.5   --output-file "$sbom_dir/cyrene-reactor-runtime.cdx.json"

# Product 依赖图
(cd product && uv export --frozen --all-groups --format cyclonedx1.5   --output-file "$sbom_dir/cyrene-reactor-product.cdx.json")

# 包含校验和与精确 git 修订的 Rust 依赖图
cargo metadata --locked --format-version 1   > "$sbom_dir/cyrene-reactor-rust-metadata.json"
```

公开源码或二进制发布前，必须检查生成报告中的 `UNDECLARED` 许可证和新增 git 依赖。本地导出成功不等于法律批准。
