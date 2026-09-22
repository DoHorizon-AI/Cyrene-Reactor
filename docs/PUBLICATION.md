# Public-source publication note / 公开源码发布说明

## Current position / 当前状态

Reactor is a public `PUBLIC_PRODUCT` source repository. The machine-readable
policy and service manifest describe the current visibility as `public`. Its
public history starts from the approved clean root; former private development
history belongs only to the separate private archive.

Reactor 已作为公开的 `PUBLIC_PRODUCT` 源码仓库托管。机器可读策略与服务清单均将当前
可见性描述为 `public`。公开历史从已批准的 clean root 开始；原私有开发历史只保留在
独立的私有归档中。

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
| Python runtime and Product tests | Local tests plus executed exact-SHA GitHub Actions | Production deployment |
| Rust host-placement checks | Locked CI build/test with only Apache-2.0 direct Platform dependencies | Full transitive legal review or a published binary |
| `execution.engine.v1` | Direct Plugins seam; no concrete engine source in Reactor | Real accelerator acceptance for every engine/provider |
| Exchange handoff | Explicit Product adapter with fail-closed behavior | Live Exchange availability or credentials |
| Release automation | No repository release workflow is present | A published package, image, or immutable release tag |

| 表面 | 当前真实状态 | 不能证明什么 |
| --- | --- | --- |
| Python runtime 与 Product 测试 | 本地测试及已实际执行的 exact-SHA GitHub Actions | 生产部署 |
| Rust host-placement 检查 | 仅含 Apache-2.0 Platform 直接依赖的锁定 CI 构建/测试 | 完整传递法律审查或已发布二进制 |
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

1. 锁定的 Plugins runtime revision 是 git 依赖，但其上游 manifest 当前没有声明许可证。
   必须补齐明确许可证元数据，并确保该依赖可公开克隆。

## Closed gates / 已关闭门禁

- Host placement validates the public protobuf projection locally and no longer
  resolves or links the AGPL `cy-adapter-client`; CI prevents regression.
- The pinned Platform and Yield revisions are anonymously fetchable and are
  resolved by executed GitHub Actions jobs.
- Exact-SHA GitHub Actions jobs execute real checks; skipped or zero-step runs
  are still never treated as evidence.

- Host placement 在本地校验公开 protobuf 投影，不再解析或链接 AGPL
  `cy-adapter-client`，且 CI 会防止回归。
- 锁定的 Platform 与 Yield revision 可匿名获取，并已由实际执行的 GitHub Actions job
  完成解析。
- exact-SHA GitHub Actions job 会执行真实检查；skipped 或零步骤运行仍不能视为证据。

See [`DEPENDENCY-LICENSES.md`](DEPENDENCY-LICENSES.md) for the license and
SBOM entrypoints, and [`SECURITY.md`](../SECURITY.md) for the threat-boundary
disclaimer.

许可证与 SBOM 入口见 [`DEPENDENCY-LICENSES.md`](DEPENDENCY-LICENSES.md)，安全边界限制见
[`SECURITY.md`](../SECURITY.md)。
