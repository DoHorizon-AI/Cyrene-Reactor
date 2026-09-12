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
