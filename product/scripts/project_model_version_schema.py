"""Project the pinned Yield ModelVersion schema into Reactor's contract tree.

The source bytes remain owned by Yield. Reactor only rebases the relative
ArtifactRef link for its generated consumer projection.

源 Schema 由 Yield 负责；Reactor 只调整 ArtifactRef 的相对路径并记录来源哈希。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

YIELD_REPOSITORY = "DoHorizon-AI/Cyrene-Yield"
YIELD_REVISION = "6fea8f835ce2561aaed4b0d9996856f6a3ef1ee6"
YIELD_SCHEMA = "contracts/product/v1/model-version.schema.json"
SOURCE_ARTIFACT_REF = "./generated/platform/artifact-ref.schema.json"
PROJECTED_ARTIFACT_REF = "../platform/artifact-ref.schema.json"


def _project(value: Any) -> Any:
    """Rebase only the known ArtifactRef link while preserving schema meaning.

        中文:仅重设已知的 ArtifactRef 链接,同时保持架构语义不变。"""

    if isinstance(value, dict):
        return {key: _project(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_project(child) for child in value]
    if value == SOURCE_ARTIFACT_REF:
        return PROJECTED_ARTIFACT_REF
    return value


def _git_show(repository: Path, revision: str, path: str) -> bytes:
    """Read one immutable Git object without modifying the source checkout.

        中文:读取一个不可变的 Git 对象,不修改源码检出目录。"""

    return subprocess.check_output(["git", "-C", str(repository), "show", f"{revision}:{path}"])


def main() -> None:
    """Write or verify the generated schema and its immutable provenance.

        中文:写入或验证生成的架构及其不可变来源信息。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--yield-repository", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source = _git_show(args.yield_repository, YIELD_REVISION, YIELD_SCHEMA)
    document = json.loads(source)
    projected = (json.dumps(_project(document), indent=2, ensure_ascii=False) + "\n").encode()
    provenance = (
        json.dumps(
            {
                "repository": YIELD_REPOSITORY,
                "revision": YIELD_REVISION,
                "sha256": {YIELD_SCHEMA: hashlib.sha256(source).hexdigest()},
                "projectionSha256": {
                    "model-version.schema.json": hashlib.sha256(projected).hexdigest()
                },
                "transform": "rebase ArtifactRef reference for Reactor generated tree",
            },
            indent=2,
        )
        + "\n"
    ).encode()

    root = Path(__file__).resolve().parents[2]
    output = root / "contracts" / "product" / "v1" / "generated" / "yield"
    outputs = {
        output / "model-version.schema.json": projected,
        output / "lifecycle-sources.json": provenance,
    }
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_bytes() != content:
                raise RuntimeError(f"generated Yield projection differs: {path.name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    print(json.dumps({"yieldRevision": YIELD_REVISION, "modelVersionProjectionVerified": True}))


if __name__ == "__main__":
    main()
