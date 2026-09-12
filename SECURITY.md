# Security policy / 安全政策

## Reporting a vulnerability / 报告漏洞

Please do not open a public issue for an unpatched vulnerability. Use GitHub
private vulnerability reporting when it is enabled for this repository. If that
channel is unavailable, contact the DoHorizon-AI repository maintainers through
the organisation's private security channel. Include only a minimal
reproduction, affected revision or component, deployment assumptions, and the
expected security boundary. Do not include credentials, tokens, tenant data,
model weights, or private endpoint details.

请勿在公开 issue 中披露尚未修复的漏洞。仓库启用 GitHub 私密漏洞报告后，请
优先使用该渠道；如果该渠道不可用，请通过 DoHorizon-AI 组织的私密安全渠道联系
维护者。仅提供最小复现、受影响的版本或组件、部署前提与预期安全边界，不要包含
凭据、令牌、租户数据、模型权重或私有端点详情。

## Security boundary / 安全边界

Reactor owns Product serving state, admission, scheduling, and fail-closed
handoffs. Platform owns process, identity, lease, fence, and hardware-fact
authority. Concrete serving engines run behind the Plugins-owned
`execution.engine.v1` contract. A `CYRENE_SERVING_CONNECTION_REF` is an opaque,
Platform-resolved endpoint grant; it is not a credential and must not be
committed to source control.

Reactor 负责产品层服务状态、准入、调度与 fail-closed 交接。Platform 负责进程、身份、
租约、围栏与硬件事实权威。具体服务引擎通过 Plugins 所有的
`execution.engine.v1` 契约运行。`CYRENE_SERVING_CONNECTION_REF` 是由 Platform
解析的透明端点授权引用，不是凭据，不得提交到源码库。

## Important non-guarantees / 重要限制

- Passing local tests or a schema check is not proof of hostile-code containment,
  tenant isolation, or production GPU security.
- Real accelerator, deployment, and cross-Product acceptance require the
  separately documented protected environment; the public-source checks are
  CPU-oriented and fail closed when a required endpoint is absent.
- Test doubles, loopback endpoints, archived evidence, and example credentials
  are not production authentication or authorization evidence.
- Publishing the source does not publish credentials, deployment configuration,
  model weights, datasets, or private infrastructure.

- 本地测试或 schema 检查通过，不代表能够隔离恶意代码、租户或生产 GPU 安全边界。
- 真实加速器、部署与跨产品验收需要单独记录的受保护环境；公开源码检查以 CPU 为主，
  所需端点缺失时会 fail closed。
- 测试替身、回环端点、归档证据与示例凭据不构成生产认证或授权证据。
- 公开源码不会公开凭据、部署配置、模型权重、数据集或私有基础设施。
