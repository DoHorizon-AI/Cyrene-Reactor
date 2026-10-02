# Repository Lifecycle: Cyrene-Reactor / 仓库生命周期：Cyrene-Reactor

This document records the current lifecycle, ownership, and publication
boundary for **Cyrene-Reactor**. The machine-readable authority is
[`repository-policy.yaml`](../repository-policy.yaml).

本文记录 **Cyrene-Reactor** 当前的生命周期、职责与公开发布边界。机器可读权威文件是
[`repository-policy.yaml`](../repository-policy.yaml)。

## 1. Purpose and ownership / 目的与职责

Reactor is a `PUBLIC_PRODUCT` source component for model inference and serving.
It owns serving Product semantics, deployment desired state, admission,
request scheduling, endpoint state, and serving lifecycle coordination.

Reactor 是面向模型推理与服务的 `PUBLIC_PRODUCT` 源码组件，负责服务产品语义、部署期望
状态、准入、请求调度、端点状态与服务生命周期协调。

Reactor does not own generic process isolation, low-level hardware facts,
concrete serving engines, cache implementations, training, evaluation, or
public gateway authentication. Those boundaries remain with Platform,
Plugins, Yield, Echo, and Exchange respectively.

Reactor 不负责通用进程隔离、底层硬件事实、具体服务引擎、缓存实现、训练、评估或公共
网关认证；这些边界分别归 Platform、Plugins、Yield、Echo 与 Exchange。

## 2. Classification and release units / 分类与发布单元

| Field | Value |
| --- | --- |
| Lifecycle class | `PUBLIC_PRODUCT` |
| Publication target visibility | `public` |
| Live hosting status | May remain `private` until an explicit owner switch and read-back |
| Source owner | Cyrene Inference Product Team |
| Independent build | Yes: `uv`/Python and Cargo |
| Package units | `cyrene-reactor-product`; `cy-exec`; `cy-exec-pro`; `cyrene-reactor-host-placement` |
| Release role | `COMPONENT_RELEASE` |
| Standalone user product | No; consumed as a Cyrene distribution component |
| Remote default branch | `main` |
| Integration branch | `develop` |
| Release branch | `main` |

The public source history starts at a single parentless `main` commit created
from the reviewed candidate tree. The former development repository, including
all branches, tags, pull-request refs, and reflogs, is retained only as a
private recovery archive and is not part of the public repository.

公开源码历史从审核后的候选树创建的单个无父 `main` 提交开始。原开发仓库的全部分支、标签、
pull-request refs 与 reflog 仅保留在私有恢复归档中，不属于公开仓库。

| 字段 | 值 |
| --- | --- |
| 生命周期分类 | `PUBLIC_PRODUCT` |
| 公开发布目标可见性 | `public` |
| 当前托管状态 | 在所有者明确切换并回读前可能仍为 `private` |
| 源码所有者 | Cyrene Inference Product Team |
| 独立构建 | 是：`uv`/Python 与 Cargo |
| 包单元 | `cyrene-reactor-product`；`cy-exec`；`cy-exec-pro`；`cyrene-reactor-host-placement` |
| 发布角色 | `COMPONENT_RELEASE` |
| 独立用户产品 | 否；作为 Cyrene 分发组件被消费 |
| 远程默认分支 | `main` |
| 集成分支 | `develop` |
| 发布分支 | `main` |

## 3. CI and release authorities / CI 与发布权威

GitHub Actions is the `github` authority for automatic source and Product
contract checks. The workflows are [`ci.yml`](../.github/workflows/ci.yml) and
[`product-contract.yml`](../.github/workflows/product-contract.yml).

GitHub Actions 是自动源码与产品契约检查的 `github` 权威，workflow 为
[`ci.yml`](../.github/workflows/ci.yml) 与
[`product-contract.yml`](../.github/workflows/product-contract.yml)。

The `Immutable component release` GitHub Actions workflow is the publisher for
attested Reactor component artifacts. The Azure definition remains a manual
supplemental lane for exact cross-repository, protected-resource, or GPU/runtime
acceptance; it is not a second automatic source authority. The GitHub Container
Apps consumer updates the existing Reactor app only after it verifies the
exact source-SHA index, manifest, OCI digest, and GitHub attestation.

`Immutable component release` GitHub Actions workflow 是 Reactor 组件制品的发布方，并为制品
提供 attestation。Azure 定义仍用于精确跨仓库、受保护资源或 GPU/runtime 验收的手动补充通道，
不是第二个自动源码权威。GitHub Container Apps 消费 workflow 只有在验证精确源码 SHA 对应的
index、manifest、OCI digest 与 GitHub attestation 后，才会更新已有 Reactor app。

## 3.1 Immutable component delivery / 不可变组件交付

Successful component-release runs on `main` and `release` use the stable
channel; `develop` uses preview. The Azure workflow resolves the immutable
release for the triggering commit and refuses a missing or mismatched release.
Manual dispatch uses its current branch and commit under the same verification.
The consumer does not build or push an image, use a mutable tag, or create an
Azure app. Existing Azure OIDC and Reactor auth rollout checks, internal
ingress enforcement, and healthy-revision/image verification remain in force.

`main` 和 `release` 上的成功组件发布运行使用 stable channel；`develop` 使用 preview。Azure
workflow 按触发提交查找不可变 release；release 缺失或不匹配时会拒绝部署。手动触发也会按当前
分支和提交执行相同验证。消费端不会构建或推送镜像、使用可变 tag 或创建 Azure app。现有 Azure
OIDC 与 Reactor auth rollout 检查、内网 ingress 限制，以及健康 revision/镜像验证均保持不变。

## 4. Public-source boundary / 公开源码边界

The target is a public source clone with no private checkout, credential,
tenant data, model weight, or deployment secret required for the CPU-oriented
source checks. The current lockfiles still reference Plugins, Platform, and
Yield git revisions; their anonymous cloneability and license closure must be
confirmed before the hosting setting is switched.

目标是公开源码克隆后无需私有 checkout、凭据、租户数据、模型权重或部署密钥即可运行以
CPU 为主的源码检查。当前锁文件仍引用 Plugins、Platform 与 Yield 的 git revision；在
切换托管可见性前，必须确认这些依赖可匿名克隆且许可证闭合。

The detailed dependency and SBOM record is
[`DEPENDENCY-LICENSES.md`](DEPENDENCY-LICENSES.md). It records the unresolved
Plugins license metadata and the Platform `AGPL-3.0-only` `cy-adapter-client`
dependency; Reactor's Apache-2.0 license does not relicense either dependency.

详细依赖与 SBOM 记录见 [`DEPENDENCY-LICENSES.md`](DEPENDENCY-LICENSES.md)，其中记录了
尚未解决的 Plugins 许可证元数据，以及 Platform 的 `AGPL-3.0-only`
`cy-adapter-client` 依赖；Reactor 的 Apache-2.0 不会重新授权任何一个依赖。

## 5. Evidence and maturity / 证据与成熟度

Local tests establish implementation and contract behavior. They do not by
themselves establish hosted exact-SHA CI, real GPU/provider acceptance,
production security, or a published package. `WIRED_NOT_RUN`, skipped, zero-step,
quota-blocked, and credential-blocked results retain those meanings and must
not be reported as `PASS`.

本地测试建立实现与契约行为证据，但不能单独证明 hosted exact-SHA CI、真实 GPU/提供方验收、
生产安全或已发布包。`WIRED_NOT_RUN`、skipped、zero-step、配额阻塞与凭据阻塞必须保留原
有含义，不能报告为 `PASS`。

Concrete serving engines remain Plugins-owned. Reactor's `DIRECT_PLUGIN`
profile and Product lifecycle are documented in [`API.md`](API.md); real
accelerator acceptance remains a separate protected-resource gate.

具体服务引擎仍由 Plugins 所有。Reactor 的 `DIRECT_PLUGIN` 配置档与产品生命周期见
[`API.md`](API.md)；真实加速器验收仍是单独的受保护资源门槛。

## 6. Branch and version policy / 分支与版本策略

- Daily work targets `develop`; release candidates are promoted to protected
  `main` through review.
- Versions use repository-scoped SemVer and immutable `v{version}` tags.
- A defective release requires a new patch version; published tags are not
  rewritten.

- 日常工作进入 `develop`；发布候选经审查提升到受保护的 `main`。
- 版本采用仓库范围的 SemVer，并使用不可变的 `v{version}` tag。
- 有缺陷的发布必须生成新的 patch 版本，不能重写已发布 tag。

See [`PUBLICATION.md`](PUBLICATION.md) for the pre-switch checklist and
remaining public-release blockers.

公开发布切换前检查与剩余阻塞项见 [`PUBLICATION.md`](PUBLICATION.md)。
