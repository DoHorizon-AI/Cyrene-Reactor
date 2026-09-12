# Local CUDA acceptance summary / 本地 CUDA 验收摘要

This page preserves the provider-neutral outcome of a protected local CUDA
acceptance run. Raw receipts, process observations, private endpoints, runtime
paths, request identifiers, GPU identifiers, and operator credentials are not
part of the public source snapshot. The retained statements are historical
local evidence; they do not claim hosted CI, a public binary release, or
production security.

本页保留受保护本地 CUDA 验收的与提供方无关的结果。原始回执、进程观察、私有端点、运行时
路径、请求标识符、GPU 标识符与操作者凭据不进入公开源码快照。以下内容属于历史本地证据，
不代表 hosted CI、公开二进制发布或生产安全已经完成。

## Recorded outcomes / 已记录结果

| Surface | Recorded result / 已记录结果 |
| --- | --- |
| Product deployment | PASS — a real deployment reached `READY` through the Product API / 真实部署通过 Product API 达到 `READY` |
| Inference and streaming | PASS — normal and incremental responses were observed / 普通请求与增量响应均已观察到 |
| Cancellation | PASS — the upstream runtime stopped a running request before its configured limit / 上游运行时在配置上限前停止运行中请求 |
| Lease and resource release | PASS — the canonical release reached `RELEASED` and resource cleanup completed / 标准释放达到 `RELEASED` 且资源清理完成 |
| Restart | PASS — the same logical serving resource restarted with a new worker allocation / 同一逻辑服务资源以新的 worker 分配完成重启 |
| Exchange handoff | PASS — a draft route required explicit confirmation before activation / 草稿路由必须显式确认后才能激活 |
| Navigator handoff | PASS — the existing client received a streamed response / 既有客户端收到流式响应 |
| Original service restoration | PASS — the operator restored the pre-existing local service after acceptance / 验收后操作者恢复原有本地服务 |
| Hosted CI | `BLOCKED_EXTERNAL` — the inspected run had zero executed steps because of billing capacity / 因 billing 容量限制，检查到的运行没有执行 step |

The protected run used one local NVIDIA CUDA device and a small reference model
whose distribution terms were checked separately. It did not establish
multi-host, multi-tenant, Windows desktop, cloud, or every-engine acceptance.
The model artifact is metadata-only in this repository; model weights and
operator setup remain outside version control.

本地受保护运行使用一个 NVIDIA CUDA 设备，并单独核对了小型参考模型的分发条款。它没有
证明多主机、多租户、Windows 桌面、云端或所有引擎均已验收。本仓库只保留模型元数据，不
包含模型权重；操作者配置仍在版本控制之外。

## Reproduction boundary / 复核边界

Use the CPU-oriented source checks in [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
for a clean checkout. A real accelerator run additionally requires a protected
Platform/Plugins environment, freshly read resource references, and local
credentials. Never copy those values into an issue, pull request, source file,
or public evidence record.

干净检出后请按 [`CONTRIBUTING.md`](../../CONTRIBUTING.md) 运行以 CPU 为主的源码检查。真实
加速器运行还需要受保护的 Platform/Plugins 环境、重新读取的资源引用与本地凭据。不要把
这些值复制到 issue、pull request、源码或公开证据记录中。

## Evidence retention / 证据保留

The detailed machine-readable receipts were deliberately removed from this
public-source candidate because they contained environment-specific identifiers
and paths. They remain recoverable only through the owner-only pre-replacement
archive; their absence is not a claim that hosted or public reproducibility has
been achieved.

详细机器回执因包含环境特定标识符与路径，已从公开源码候选中有意移除。它们仅能从替换前
的 owner-only 归档恢复；移除不代表 hosted 或公开可复现性已经完成。
