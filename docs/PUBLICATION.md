# Public-source publication note / 公开源码发布说明

## Current position / 当前状态

Reactor is prepared as a `PUBLIC_PRODUCT` source repository. The machine-readable
policy and service manifest describe the intended target visibility as `public`.
The public replacement must start from one parentless `main` commit; the former
development history, branches, tags, pull-request refs, and reflogs belong only
to a separate private archive. The GitHub hosting setting remains an explicit
owner operation and must be switched and read back only after the gates below.

Reactor 已按 `PUBLIC_PRODUCT` 源码仓库准备。机器可读策略与服务清单将目标可见性描述为
`public`。公开替换仓库必须从一个无父提交的 `main` 开始；原开发历史、分支、标签、pull-
request refs 与 reflog 只保留在独立的私有归档中。GitHub 托管可见性仍需所有者在下方门禁
完成后明确切换并回读。

The integration model is `develop` for daily work and `main` for releases. The
automatic source and Product contract checks are the GitHub Actions workflows
under `.github/workflows/`. The Azure pipeline is a manual supplemental lane
for protected credentials, exact cross-repository acceptance, deployment, or
GPU/runtime evidence.

日常集成分支为 `develop`，发布分支为 `main`。自动源码与产品契约检查由
`.github/workflows/` 下的 GitHub Actions workflow 负责。Azure pipeline 仅作为需要受保护
凭据、精确跨仓库验收、部署或 GPU/runtime 证据时的手动补充通道。

## Evidence boundary / 证据边界

| Surface | Current honest status | What it does not prove |
| --- | --- | --- |
| Python runtime and Product tests | Local implementation and tests | Hosted exact-SHA execution or production deployment |
| Rust host-placement checks | Local locked build/test surface | A complete public binary distribution license grant |
| `execution.engine.v1` | Direct Plugins seam; no concrete engine source in Reactor | Real accelerator acceptance for every engine/provider |
| Exchange handoff | Explicit Product adapter with fail-closed behavior | Live Exchange availability or credentials |
| Release automation | No repository release workflow is present | A published package, image, or immutable release tag |

| 表面 | 当前真实状态 | 不能证明什么 |
| --- | --- | --- |
| Python runtime 与 Product 测试 | 本地实现与测试 | hosted exact-SHA 执行或生产部署 |
| Rust host-placement 检查 | 本地锁定构建/测试表面 | 完整公开二进制分发许可 |
| `execution.engine.v1` | Plugins 直连接缝；Reactor 不含具体引擎源码 | 每个引擎/提供方都已完成真实加速器验收 |
| Exchange 交接 | 显式 Product 适配器，失败时 fail closed | Exchange 真实可用或凭据已配置 |
| 发布自动化 | 当前没有仓库级发布 workflow | 已发布包、镜像或不可变 release tag |

The status names in [`API.md`](API.md) describe implementation or local
contract evidence. They must not be read as hosted, GPU, security, or release
acceptance. Concrete serving engines remain Plugins-owned; Reactor's lockfiles
must be installable without an unannounced private checkout before anonymous
cloning is claimed.

[`API.md`](API.md) 中的状态名称只描述实现或本地契约证据，不代表 hosted、GPU、安全或发布
验收。具体服务引擎仍由 Plugins 所有；在没有未声明的私有 checkout 的情况下能够安装当前
锁文件后，才能声称支持匿名克隆。

## Publication blockers / 公开发布阻塞项

1. The locked Plugins runtime revision is a git dependency whose upstream
   manifest currently does not declare a license. The dependency must receive
   explicit license metadata and be publicly cloneable.
2. The Rust host-placement path resolves Platform's `AGPL-3.0-only`
   `cy-adapter-client`. Legal review must decide whether to distribute that
   binary path, separate the dependency, or publish the applicable source and
   notices.
3. Platform and Yield contract references are immutable git revisions today;
   their public cloneability and exact-SHA availability must be confirmed before
   an anonymous clean-clone build.
4. A fresh exact-SHA GitHub Actions run must execute real jobs and pass. A
   zero-step, quota, credential, or skipped result is `NOT_RUN`/`BLOCKED`, not
   `PASS`.

1. 锁定的 Plugins runtime revision 是 git 依赖，但其上游 manifest 当前没有声明许可证。
   必须补齐明确许可证元数据，并确保该依赖可公开克隆。
2. Rust host-placement 路径解析到 Platform 的 `AGPL-3.0-only`
   `cy-adapter-client`。必须通过法律审查决定是否分发该二进制路径、拆分依赖，或同时
   发布适用的源码与声明。
3. Platform 与 Yield 契约目前使用不可变 git revision；必须在匿名 clean-clone 构建前确认
   它们可公开克隆并能按精确 SHA 获取。
4. 必须有一次针对精确 SHA、实际执行 job 并通过的 GitHub Actions 运行。零步骤、配额、
   凭据或 skipped 结果均属于 `NOT_RUN`/`BLOCKED`，不能写成 `PASS`。

See [`DEPENDENCY-LICENSES.md`](DEPENDENCY-LICENSES.md) for the license and
SBOM entrypoints, and [`SECURITY.md`](../SECURITY.md) for the threat-boundary
disclaimer.

许可证与 SBOM 入口见 [`DEPENDENCY-LICENSES.md`](DEPENDENCY-LICENSES.md)，安全边界限制见
[`SECURITY.md`](../SECURITY.md)。
