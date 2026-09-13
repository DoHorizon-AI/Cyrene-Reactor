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

The `cyrene-reactor-host-placement` package is Apache-2.0 itself, but its
resolved Platform dependencies retain their own licenses. In particular,
`cy-adapter-client` is `AGPL-3.0-only`; distributing a binary that links it
requires a separate legal review and the applicable source/notice obligations.

`cyrene-reactor-host-placement` 包自身是 Apache-2.0，但解析到的 Platform 依赖仍保留
各自许可证。特别是 `cy-adapter-client` 为 `AGPL-3.0-only`；分发链接该依赖的二进制
需要单独法律审查，并履行适用的源码与声明义务。

| Package | Revision or version | SPDX license | Source / note |
| --- | --- | --- | --- |
| `cy-execution-fabric` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `Apache-2.0` | Platform execution attachment contract. |
| `cy-adapter-client` | Platform `c59be6f2bd82489fbe933dadff84fc589e00afd9` | `AGPL-3.0-only` | Platform local IPC client; public binary distribution is a legal review gate. |
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
reviewed for `UNDECLARED` licenses, the AGPL Platform dependency, and any
new git dependency. A successful local export is not a legal approval.

公开源码或二进制发布前，必须审查生成报告中的 `UNDECLARED` 许可证、AGPL Platform
依赖与新增 git 依赖。本地导出成功不等于法律批准。
