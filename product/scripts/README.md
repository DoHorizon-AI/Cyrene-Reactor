# Product maintenance / 产品维护

`project_model_version_schema.py --yield-repository PATH [--check]` reads the
exact Yield revision pinned by the Reactor Product dependency, rebases only the
ArtifactRef link, and records source and projection hashes.

ModelVersion 投影脚本只读取锁定的 Yield 提交，不会修改 Yield 工作区。

The live acceptance procedure is recorded in `../evidence/cuda-acceptance-2026-09-06.md`.
Structural/unit fixtures cannot be reported as GPU or Navigator acceptance.

真实验收必须调用配置好的服务；单测不能替代 GPU 和 Navigator 验收。
