# Local composed LoRA acceptance summary / 本地组合 LoRA 验收摘要

This page preserves the provider-neutral result of a protected local composed
LoRA run. The source snapshot retains no session, deployment, endpoint, worker,
lease, GPU, port, filesystem-path, or credential identifiers from that run.
The statements below are historical local evidence and do not claim hosted CI,
model-quality improvement, a public binary release, or production security.

本页保留受保护本地组合 LoRA 运行的与提供方无关结果。源码快照不保留该运行的会话、部署、
端点、worker、lease、GPU、端口、文件系统路径或凭据标识符。以下内容属于历史本地证据，
不代表 hosted CI、模型质量提升、公开二进制发布或生产安全已经完成。

## Recorded outcomes / 已记录结果

| Surface | Recorded result / 已记录结果 |
| --- | --- |
| Composed model contract | PASS — an immutable ModelVersion was created and read back / 不可变 ModelVersion 创建并回读成功 |
| Adapter artifact validation | PASS — a deterministic adapter fixture contained 112 tensors and six negative cases rejected malformed input / 确定性 adapter fixture 含 112 个 tensor，并拒绝六类错误输入 |
| Dynamic adapter load | PASS — the serving runtime loaded the adapter and preserved its parent identity / 服务运行时动态加载 adapter 并保留 parent identity |
| READY, chat, and streaming | PASS — the adapter model reached `READY` and produced normal and incremental responses / adapter 模型达到 `READY` 并产生普通与增量响应 |
| Cancellation | PASS — an in-flight request stopped before its configured limit and a follow-up request succeeded / 运行中请求在配置上限前停止，后续请求成功 |
| Release and restart | PASS — release completed and the same logical resource restarted with a new worker allocation / 释放完成，同一逻辑资源以新的 worker 分配重启 |
| Exchange handoff | PASS — route activation required an explicit draft confirmation / 路由激活需要显式确认草稿 |
| Navigator handoff | PASS — the existing client received the composed-model response / 既有客户端收到组合模型响应 |
| Hosted CI | `BLOCKED_EXTERNAL` — billing capacity prevented inspected jobs from executing steps / billing 容量限制导致检查到的 job 未执行 step |

The fixture was generated locally with standard PEFT configuration and contains
no base-model weights. The reference base is
`Qwen/Qwen2.5-1.5B-Instruct` at revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`; its Apache-2.0 license was checked
outside the runtime receipt. Artifact digests are recorded in the protected
operator archive, not required to interpret this source tree.

该 fixture 使用标准 PEFT 配置在本地生成，不包含 base 模型权重。参考 base 为
`Qwen/Qwen2.5-1.5B-Instruct` 的 revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`；其 Apache-2.0 许可证已在运行回执之外单独
核对。制品 digest 保存在受保护操作者归档中，理解本源码树不依赖这些 digest。

## Scope and limits / 范围与限制

The run covered one local CUDA host, one base model, one adapter, and the
existing Cyrene handoff path. It did not cover multi-adapter serving,
multi-host or multi-tenant isolation, Windows, training, merge pipelines,
provider-specific engine quality, or a published package. Concrete serving
engines remain Plugins-owned and are not copied into Reactor.

本次运行覆盖一个本地 CUDA 主机、一个 base 模型、一个 adapter 与既有 Cyrene 交接路径。
未覆盖多 adapter 服务、多主机或多租户隔离、Windows、训练、merge pipeline、提供方特定
引擎质量或公开包。具体服务引擎仍归 Plugins 所有，Reactor 不复制其源码。

## Evidence retention / 证据保留

Detailed runtime receipts and cross-repository logs were deliberately removed
from this public-source candidate because they contained environment-specific
identifiers and paths. They remain recoverable only through the owner-only
pre-replacement archive; their absence is not a claim of public reproducibility.

详细运行回执与跨仓日志因包含环境特定标识符与路径，已从公开源码候选中有意移除。它们仅能
从替换前的 owner-only 归档恢复；移除不代表公开可复现性已经完成。
