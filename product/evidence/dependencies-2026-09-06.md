# Runtime dependency review / 运行依赖核对

Inspected the actual installed distributions on 2026-09-06, their LICENSE/NOTICE
files, declared requirements and primary upstream maintenance records. This is
the first existing-environment execution profile; Reactor does not distribute a
CUDA runtime image or GPU driver. Runtime metadata is recorded in
`runtime-dependencies.json`; Product and Rust dependencies are exactly locked.

本次核对实际安装包，不把旧候选推荐当作审查。执行环境为已有独立 Python 环境，
没有修改共享驱动或安装新 GPU 软件，也没有授权分发 NVIDIA 专有运行库。

| Component | Actual version | Inspected license | Declared requirements, including extras |
|---|---|---|---:|
| vLLM | 0.25.1 | Apache-2.0 | 98 |
| PyTorch | 2.11.0 (runtime reports +cu130) | BSD-3-Clause, bundled NOTICE retained | 17 |
| Transformers | 5.16.1 | Apache-2.0 | 251 |
| Hugging Face Hub | 1.29.0 | Apache-2.0 | 112 |
| grpcio | 1.83.0 | Apache-2.0 | 2 |
| protobuf | 7.36.0 | BSD-3-Clause | 0 |
| safetensors | 0.8.0 | Apache-2.0 | 36 |
| cryptography (Product signer) | 50.0.1 | Apache-2.0 OR BSD-3-Clause | Product lock |
| httpx (Product transport) | 0.28.1 | BSD-3-Clause | Product lock |
| uvicorn (Product HTTP server) | 0.52.4 | BSD-3-Clause | Product lock |

License file SHA256 values are in the JSON record. Requirements counts include
optional extras and are not installed dependency counts. `uv pip check` checked
197 installed runtime distributions and 58 Product distributions, with no
incompatible dependencies. Keep the environments separate: vLLM's FastAPI range
is `>=0.133.0,<0.137.0`; Product pins 0.141.1.

依赖数量不等于安装数量；本次依赖兼容检查为真实环境结果，不代表 GPU 部署完成。
导出的 Qwen model 包保留其 Apache-2.0 LICENSE；不包含上述 Python 环境或驱动。

Primary maintenance observations: GitHub reported all queried projects neither
archived nor disabled. Latest repository pushes observed were September 5–6 for
vLLM, Transformers, Hub, PyTorch, grpc, protobuf and cryptography; September 1 for
uvicorn. httpx's latest observed push was March 29, 2026; it is a slower-moving
dependency already used by the Products, not an inferred active release cadence.

- [vLLM 0.25.1 release](https://github.com/vllm-project/vllm/releases/tag/v0.25.1)
  confirms the selected maintenance patch release.
- [Hub 1.29.0 release](https://github.com/huggingface/huggingface_hub/releases/tag/v1.29.0)
  records download and security fixes in the selected version.
- [cryptography changelog](https://cryptography.io/en/stable/changelog/)
  records the selected 50.0.1 release.
- Other primary repositories: [PyTorch](https://github.com/pytorch/pytorch),
  [Transformers](https://github.com/huggingface/transformers),
  [grpc](https://github.com/grpc/grpc), [protobuf](https://github.com/protocolbuffers/protobuf),
  [httpx](https://github.com/encode/httpx), [uvicorn](https://github.com/Kludex/uvicorn).

上游维护观察只是该日快照，不是未来维护承诺。若要分发完整 CUDA 镜像，必须针对
实际镜像中的第三方/NVIDIA 组件另行核对分发条件；本轮没有扩大到镜像发布。
---
<!-- Chinese Translation / 中文翻译 -->

# 运行时依赖核对（2026-09-06）

核对了 2026-09-06 实际安装的发行包、其 LICENSE/NOTICE 文件、声明的依赖要求和上游主要维护记录。这是现有环境中的首个执行配置；Reactor 不分发 CUDA 运行时镜像或 GPU 驱动。运行时元数据记录在 `runtime-dependencies.json` 中；Product 和 Rust 依赖均由锁文件精确固定。

本次核对针对实际安装包，不把旧候选推荐当作审查结论。执行环境是已有的独立 Python 环境；没有修改共享驱动、没有安装新的 GPU 软件，也没有授权分发 NVIDIA 专有运行库。

| 组件 | 实际版本 | 已检查许可证 | 声明的依赖项，含 extras |
|---|---|---|---:|
| vLLM | 0.25.1 | Apache-2.0 | 98 |
| PyTorch | 2.11.0（运行时报告 +cu130） | BSD-3-Clause，保留随包提供的 NOTICE | 17 |
| Transformers | 5.16.1 | Apache-2.0 | 251 |
| Hugging Face Hub | 1.29.0 | Apache-2.0 | 112 |
| grpcio | 1.83.0 | Apache-2.0 | 2 |
| protobuf | 7.36.0 | BSD-3-Clause | 0 |
| safetensors | 0.8.0 | Apache-2.0 | 36 |
| cryptography（Product 签名器） | 50.0.1 | Apache-2.0 OR BSD-3-Clause | Product 锁文件 |
| httpx（Product 传输） | 0.28.1 | BSD-3-Clause | Product 锁文件 |
| uvicorn（Product HTTP 服务器） | 0.52.4 | BSD-3-Clause | Product 锁文件 |

许可证文件的 SHA256 值记录在 JSON 文件中。依赖要求计数包含可选 extras，并不代表已安装依赖数量。`uv pip check` 检查了 197 个已安装运行时发行包和 58 个 Product 发行包，没有发现不兼容依赖。环境应保持隔离：vLLM 的 FastAPI 范围为 `>=0.133.0,<0.137.0`，而 Product 固定使用 0.141.1。

依赖要求数量不等于实际安装数量。本次依赖兼容检查是在真实环境中得到的结果，不代表 GPU 部署已完成。导出的 Qwen 模型包保留其 Apache-2.0 LICENSE；该包不包含上述 Python 环境或驱动。

上游维护情况观察：GitHub 报告所查询项目均未归档或停用。观察到 vLLM、Transformers、Hub、PyTorch、grpc、protobuf 和 cryptography 仓库的最近推送日期为 9 月 5 至 6 日；uvicorn 为 9 月 1 日。httpx 最近一次观察到的推送是 2026 年 3 月 29 日；它是各 Product 已在使用的较慢更新依赖，此处没有据此推断活跃发布节奏。

- [vLLM 0.25.1 发布记录](https://github.com/vllm-project/vllm/releases/tag/v0.25.1)确认了所选维护补丁版本。
- [Hub 1.29.0 发布记录](https://github.com/huggingface/huggingface_hub/releases/tag/v1.29.0)记录了该版本所选用的下载和安全修复。
- [cryptography 更新日志](https://cryptography.io/en/stable/changelog/)记录了所选的 50.0.1 版本。
- 其他上游项目：[PyTorch](https://github.com/pytorch/pytorch)、[Transformers](https://github.com/huggingface/transformers)、[grpc](https://github.com/grpc/grpc)、[protobuf](https://github.com/protocolbuffers/protobuf)、[httpx](https://github.com/encode/httpx)、[uvicorn](https://github.com/Kludex/uvicorn)。

上游维护情况只是该日期的快照，不构成未来维护承诺。若要分发完整 CUDA 镜像，必须针对镜像中的实际第三方/NVIDIA 组件另行核对分发条件；本次记录没有扩大到镜像发布审查。
