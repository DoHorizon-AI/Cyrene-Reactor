"""Project the pinned Platform ArtifactRef schema into Reactor's contract tree.

Platform owns generic content identity. Reactor owns deployment and endpoint
semantics and consumes only an immutable, provenance-recorded projection.

Platform 维护通用制品身份；Reactor 维护部署语义，并保留可复核的精确投影。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PLATFORM_REPOSITORY = "DoHorizon-AI/Cyrene-Platform"
PLATFORM_REVISION = "c59be6f2bd82489fbe933dadff84fc589e00afd9"
PLATFORM_SCHEMA = "contracts/schemas/manifests/artifact_ref.schema.json"


def _git_show(repository: Path, revision: str, path: str) -> bytes:
    """Read one immutable source object without modifying Platform. | 读取精确对象。"""

    return subprocess.check_output(["git", "-C", str(repository), "show", f"{revision}:{path}"])


def main() -> None:
    """Write or verify the generated schema and provenance. | 写入或校验投影。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--platform-repository", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source = _git_show(args.platform_repository, PLATFORM_REVISION, PLATFORM_SCHEMA)
    json.loads(source)
    provenance = (
        json.dumps(
            {
                "repository": PLATFORM_REPOSITORY,
                "revision": PLATFORM_REVISION,
                "sha256": {PLATFORM_SCHEMA: hashlib.sha256(source).hexdigest()},
            },
            indent=2,
        )
        + "\n"
    ).encode()

    root = Path(__file__).resolve().parents[2]
    output = root / "contracts/product/v1/generated/platform"
    outputs = {
        output / "artifact-ref.schema.json": source,
        output / "lifecycle-sources.json": provenance,
    }
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_bytes() != content:
                raise RuntimeError(f"generated Platform projection differs: {path.name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    print(json.dumps({"platformRevision": PLATFORM_REVISION, "artifactRefVerified": True}))


if __name__ == "__main__":
    main()
