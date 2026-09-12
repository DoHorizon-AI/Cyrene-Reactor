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
