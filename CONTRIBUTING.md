# Contributing to Cyrene-Reactor

Reactor is a Product repository. Keep serving state and Product coordination
here; concrete engines, generic lifecycle, hardware facts, caches, and training
belong to their canonical owners. Read the [Cyrene Contribution
Workflow](https://github.com/DoHorizon-AI/Cyrene-Platform/blob/main/docs/governance/contribution-workflow.md)
before opening a pull request.

## Local verification

Run the checks for the surfaces you changed:

```bash
# Rust host-placement component
cargo fmt --all -- --check
cargo check --locked --workspace --all-targets
cargo clippy --locked --workspace --all-targets -- -D warnings
cargo test --locked --workspace

# Runtime core and Pro extensions
uv sync --frozen --extra dev
uv run --frozen ruff check runtime/core/src runtime/core/tests runtime/pro/src runtime/pro/tests
uv run --frozen python -m pytest runtime/core/tests/ runtime/pro/tests/

# Product API and contracts
cd product
uv sync --frozen --group dev
uv run --no-sync ruff check src tests
uv run --no-sync ruff format --check src tests
uv run --no-sync mypy
uv run --no-sync pytest -q tests
```

GitHub Actions in `.github/workflows/` owns automatic source and contract
checks. The Azure pipeline is a manual supplemental lane for exact
cross-repository, deployment, or protected-resource acceptance; it does not
replace the public-source checks.

## Documentation, dependencies, and security

- Add or substantially change `docs/` pages in English and Chinese, and update
  [`docs/README.md`](docs/README.md).
- Keep `uv.lock` and `Cargo.lock` consistent with manifests. Review
  [`docs/DEPENDENCY-LICENSES.md`](docs/DEPENDENCY-LICENSES.md) before adding a
  dependency or changing a pinned upstream revision.
- Never commit credentials, private endpoints, tenant data, model weights, or
  developer-specific absolute paths. See [`SECURITY.md`](SECURITY.md).
- Preserve the Apache-2.0 notice in [`LICENSE`](LICENSE) and retain upstream
  notices for dependencies when distributing built artifacts.
