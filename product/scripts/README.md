# Product maintenance / 产品维护

`project_model_version_schema.py --yield-repository PATH [--check]` reads the
exact Yield revision pinned by the Reactor Product dependency, rebases only the
ArtifactRef link, and records source and projection hashes.

ModelVersion 投影脚本只读取锁定的 Yield 提交，不会修改 Yield 工作区。

The live acceptance procedure is recorded in `../evidence/cuda-acceptance-2026-09-06.md`.
Structural/unit fixtures cannot be reported as GPU or Navigator acceptance.

真实验收必须调用配置好的服务；单测不能替代 GPU 和 Navigator 验收。
---
<!-- Chinese Translation / 中文翻译 -->

# Product 维护脚本

`project_model_version_schema.py --yield-repository PATH [--check]` 会读取 Reactor Product 依赖固定的确切 Yield 修订版本，只调整 ArtifactRef 链接，并记录源文件和投影的哈希。

ModelVersion 投影脚本只读取固定版本的 Yield，不会修改 Yield 工作区。

实际验收流程记录在 `../evidence/cuda-acceptance-2026-09-06.md`。不能把结构/单元夹具报告为 GPU 或 Navigator 验收。

真实验收必须调用已配置的服务；单元测试不能替代 GPU 和 Navigator 验收。
