# cy-exec-pro

This directory is an optional, independently installable Pro extension for
Reactor's `runtime/core` (`cy-exec`) package. It contains only Python modules
that are unique to the Pro implementation; community execution and training
modules are not copied here.

## Install

The package is intentionally not a default member of the repository uv
workspace. From this directory, install the community package and this
plugin explicitly:

```bash
uv pip install -e ../core -e ".[dev]"
```

For a normal install without the test dependencies:

```bash
uv pip install -e ../core -e .
```

## Package layout

The package is rooted at `src/cy_exec_pro` and uses these namespaces:

- `cy_exec_pro.engines`: reserved namespace; no engine or cache implementation
- `cy_exec_pro.core`: Product-side alerts
- `cy_exec_pro.utils`: structured logging and redaction
- Training helpers are owned by Yield and concrete inference engines are owned
  by `Cyrene-Plugins-Official`; neither is part of this runtime package.

## Explicit limitations

- This package does not detect hardware, select an engine, or relay model
  inference. Those replaceable capabilities are resolved from Plugins through
  Reactor's Product port.

## Verification

From this directory:

```bash
python -m compileall -q src tests
python -m pytest -q
```

The import/compile path does not require a GPU. CUDA, Ascend, ROCm, Intel
XPU, vLLM, and TensorRT integrations remain lazy or optional.
---
<!-- Chinese Translation / 中文翻译 -->

# cy-exec-pro

此目录是 Reactor `runtime/core`（`cy-exec`）软件包的可选、可独立安装 Pro 扩展。它只包含 Pro 实现独有的 Python 模块；社区版执行和训练模块不会复制到这里。

## 安装

此软件包有意不作为仓库 uv workspace 的默认成员。从此目录显式安装社区软件包和此插件：

```bash
uv pip install -e ../core -e ".[dev]"
```

若要在不安装测试依赖的情况下正常安装：

```bash
uv pip install -e ../core -e .
```

## 软件包布局

软件包位于 `src/cy_exec_pro`，使用以下命名空间：

- `cy_exec_pro.engines`：保留命名空间；不包含引擎或缓存实现
- `cy_exec_pro.core`：Product 侧告警
- `cy_exec_pro.utils`：结构化日志和脱敏
- 训练辅助代码由 Yield 负责，具体推理由 `Cyrene-Plugins-Official` 中的引擎负责；两者都不属于此运行时软件包。

## 明确限制

- 此软件包不检测硬件、不选择引擎，也不中继模型推理。这些可替换能力由 Reactor 通过 Product 端口从 Plugins 解析。

## 验证

在此目录运行：

```bash
python -m compileall -q src tests
python -m pytest -q
```

导入/编译流程不需要 GPU。CUDA、Ascend、ROCm、Intel XPU、vLLM 和 TensorRT 集成仍为惰性加载或可选项。
