"""
┌─────────────────────────────────────────────────────────────────────┐
│  📄 store.py                                                        │
│  Module: cyrene_reactor_product.store                               │
│  Role: SQLite Product state authority and idempotency ledger.        │
│                                                                     │
│  模块职责：持久化 Deployment、Endpoint 与幂等账本。                       │
└─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock
from uuid import UUID

from cyrene_reactor_product.domain import (
    Deployment,
    DeploymentDraft,
    DeploymentEvent,
    DeploymentPhase,
    Endpoint,
    ModelImport,
)
from cyrene_reactor_product.errors import ReactorProductError


class ReactorStore:
    """Durable Product store independent of engine and Kernel state. | 产品权威存储。"""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._connection:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS deployments (
                    id TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS endpoints (
                    id TEXT PRIMARY KEY,
                    deployment_id TEXT NOT NULL UNIQUE,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deployment_drafts (
                    id TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deployment_execution_evidence (
                    deployment_id TEXT PRIMARY KEY,
                    execution_ref TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS model_imports (
                    id TEXT PRIMARY KEY,
                    document TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS idempotency (
                    scope TEXT NOT NULL,
                    key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    PRIMARY KEY(scope, key)
                );
                CREATE TABLE IF NOT EXISTS deployment_events (
                    deployment_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    message TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    failure_code TEXT,
                    PRIMARY KEY(deployment_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS idx_deployment_events_id
                    ON deployment_events(deployment_id);
                CREATE TABLE IF NOT EXISTS deployment_diagnostics (
                    deployment_id TEXT NOT NULL,
                    record_index INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    document TEXT NOT NULL,
                    PRIMARY KEY(deployment_id, record_index)
                );
                CREATE INDEX IF NOT EXISTS idx_deployment_diagnostics_sequence
                    ON deployment_diagnostics(deployment_id, sequence);
                CREATE TABLE IF NOT EXISTS deployment_diagnostics_cursors (
                    deployment_id TEXT PRIMARY KEY,
                    runtime_sequence INTEGER NOT NULL
                );
                """
            )
            self._migrate_execution_evidence()

    def _migrate_execution_evidence(self) -> None:
        """Move legacy public execution refs into the private evidence table.

        将旧公共执行引用迁移到私有证据表。
        """

        rows = self._connection.execute("SELECT id, document FROM deployments").fetchall()
        for row in rows:
            document = json.loads(row["document"])
            execution_ref = document.pop("engineExecutionRef", None)
            if not isinstance(execution_ref, str) or not execution_ref:
                continue
            self._connection.execute(
                "INSERT OR IGNORE INTO deployment_execution_evidence"
                "(deployment_id, execution_ref) VALUES (?, ?)",
                (row["id"], execution_ref),
            )
            self._connection.execute(
                "UPDATE deployments SET document = ? WHERE id = ?",
                (json.dumps(document, separators=(",", ":")), row["id"]),
            )

    def close(self) -> None:
        """Close the database connection. | 关闭数据库连接。"""

        with self._lock:
            self._connection.close()

    def create_draft(self, draft: DeploymentDraft, key: str, digest: str) -> DeploymentDraft:
        """Commit a draft and its replay receipt together. | 原子持久化草稿与幂等记录。"""
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT request_hash, resource_id FROM idempotency "
                "WHERE scope = 'deployment-draft' AND key = ?",
                (key,),
            ).fetchone()
            if row is not None:
                if row["request_hash"] != digest:
                    raise ReactorProductError(
                        code="REACTOR_IDEMPOTENCY_CONFLICT",
                        title="Draft request conflict",
                        detail="This handoff key already identifies another request.",
                        status=409,
                    )
                return self.get_draft(UUID(row["resource_id"]))
            self._connection.execute(
                "INSERT INTO deployment_drafts(id, document) VALUES (?, ?)",
                (str(draft.id), draft.model_dump_json(exclude_none=True)),
            )
            self._connection.execute(
                "INSERT INTO idempotency(scope, key, request_hash, resource_id) "
                "VALUES ('deployment-draft', ?, ?, ?)",
                (key, digest, str(draft.id)),
            )
        return draft

    def save_draft(self, draft: DeploymentDraft) -> None:
        """Persist the draft's explicit deployment receipt. | 保存显式部署回执。"""
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO deployment_drafts(id, document) VALUES (?, ?)",
                (str(draft.id), draft.model_dump_json(exclude_none=True)),
            )

    def get_draft(self, identifier: UUID) -> DeploymentDraft:
        """Read an imported draft by Product identity. | 按产品身份读取草稿。"""
        with self._lock:
            row = self._connection.execute(
                "SELECT document FROM deployment_drafts WHERE id = ?",
                (str(identifier),),
            ).fetchone()
        if row is None:
            raise ReactorProductError(
                code="REACTOR_DRAFT_NOT_FOUND",
                title="Deployment draft not found",
                detail="The selected deployment draft does not exist.",
                status=404,
            )
        return DeploymentDraft.model_validate_json(row["document"])

    def list_drafts(self) -> list[DeploymentDraft]:
        """List preparations without starting them. | 列出草稿但不启动。"""
        with self._lock:
            rows = self._connection.execute(
                "SELECT document FROM deployment_drafts ORDER BY rowid DESC"
            ).fetchall()
        return [DeploymentDraft.model_validate_json(row["document"]) for row in rows]

    def resolve_model_import_request(self, key: str | None, digest: str) -> str | None:
        """Resolve model-import replay or reject conflicting key reuse. | 解析导入幂等重放。"""

        if key is None:
            return None
        with self._lock:
            row = self._connection.execute(
                "SELECT request_hash, resource_id FROM idempotency "
                "WHERE scope = 'model-import' AND key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        if row["request_hash"] != digest:
            raise ReactorProductError(
                code="REACTOR_IDEMPOTENCY_CONFLICT",
                title="Idempotency key conflict",
                detail="The Idempotency-Key was already used with a different import request.",
                status=409,
            )
        return str(row["resource_id"])

    def commit_model_import_intent(
        self, model_import: ModelImport, key: str | None, digest: str
    ) -> str | None:
        """Persist import intent and retry identity atomically. | 原子持久化导入意图。"""

        with self._lock, self._connection:
            replay = self.resolve_model_import_request(key, digest)
            if replay is not None:
                return replay
            self._connection.execute(
                "INSERT INTO model_imports(id, document) VALUES (?, ?)",
                (str(model_import.id), model_import.model_dump_json(exclude_none=True)),
            )
            if key is not None:
                self._connection.execute(
                    "INSERT INTO idempotency(scope, key, request_hash, resource_id) "
                    "VALUES ('model-import', ?, ?, ?)",
                    (key, digest, str(model_import.id)),
                )
        return None

    def save_model_import(self, model_import: ModelImport) -> None:
        """Upsert a ModelImport validation observation. | 写入导入校验观测。"""

        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO model_imports(id, document) VALUES (?, ?)",
                (str(model_import.id), model_import.model_dump_json(exclude_none=True)),
            )

    def get_model_import(self, identifier: UUID) -> ModelImport | None:
        """Read an import by Product identity. | 按产品身份读取导入。"""

        with self._lock:
            row = self._connection.execute(
                "SELECT document FROM model_imports WHERE id = ?", (str(identifier),)
            ).fetchone()
        return ModelImport.model_validate_json(row["document"]) if row else None

    def list_model_imports(self) -> list[ModelImport]:
        """List validated imports for deployment selection. | 列出可部署的导入。"""

        with self._lock:
            rows = self._connection.execute(
                "SELECT document FROM model_imports ORDER BY rowid DESC"
            ).fetchall()
        return [ModelImport.model_validate_json(row["document"]) for row in rows]

    def save_deployment(self, deployment: Deployment) -> None:
        """Upsert a Deployment. | 写入 Deployment。"""

        document = deployment.model_dump_json(by_alias=True, exclude_none=True)
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO deployments(id, document) VALUES (?, ?)",
                (str(deployment.id), document),
            )

    def save_pair(
        self,
        deployment: Deployment,
        endpoint: Endpoint,
        *,
        execution_ref: str | None = None,
    ) -> None:
        """Atomically commit Deployment and Endpoint observations. | 原子提交两个资源。"""

        deployment_document = deployment.model_dump_json(by_alias=True, exclude_none=True)
        endpoint_document = endpoint.model_dump_json(by_alias=True, exclude_none=True)
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO deployments(id, document) VALUES (?, ?)",
                (str(deployment.id), deployment_document),
            )
            self._connection.execute(
                """
                INSERT OR REPLACE INTO endpoints(id, deployment_id, document)
                VALUES (?, ?, ?)
                """,
                (str(endpoint.id), str(endpoint.deployment_id), endpoint_document),
            )
            if execution_ref is not None:
                self._connection.execute(
                    "INSERT OR REPLACE INTO deployment_execution_evidence"
                    "(deployment_id, execution_ref) VALUES (?, ?)",
                    (str(deployment.id), execution_ref),
                )

    def get_execution_ref(self, deployment_id: UUID) -> str | None:
        """Read internal execution evidence without Product exposure.

        读取不会暴露到产品 JSON 的内部执行证据。
        """

        with self._lock:
            row = self._connection.execute(
                "SELECT execution_ref FROM deployment_execution_evidence WHERE deployment_id = ?",
                (str(deployment_id),),
            ).fetchone()
        return str(row["execution_ref"]) if row else None

    def get_deployment(self, deployment_id: UUID) -> Deployment | None:
        """Read a Deployment. | 读取 Deployment。"""

        with self._lock:
            row = self._connection.execute(
                "SELECT document FROM deployments WHERE id = ?", (str(deployment_id),)
            ).fetchone()
        return Deployment.model_validate_json(row["document"]) if row else None

    def list_deployments(self) -> list[Deployment]:
        """Read persisted resources for recovery and Open in navigation. | 列出现有资源。"""
        with self._lock:
            rows = self._connection.execute(
                "SELECT document FROM deployments ORDER BY rowid DESC"
            ).fetchall()
        return [Deployment.model_validate_json(row["document"]) for row in rows]

    def create_intent(self, deployment: Deployment, key: str | None, digest: str) -> str | None:
        """Persist intent and retry identity atomically before execution. | 原子创建意图。"""
        with self._lock, self._connection:
            replay = self.resolve_idempotency(key, digest)
            if replay is not None:
                return replay
            self._connection.execute(
                "INSERT INTO deployments(id, document) VALUES (?, ?)",
                (str(deployment.id), deployment.model_dump_json(exclude_none=True)),
            )
            if key is not None:
                self._connection.execute(
                    "INSERT INTO idempotency(scope, key, request_hash, resource_id) "
                    "VALUES ('create-deployment', ?, ?, ?)",
                    (key, digest, str(deployment.id)),
                )
        return None

    def get_endpoint(self, endpoint_id: UUID) -> Endpoint | None:
        """Read an Endpoint. | 读取 Endpoint。"""

        with self._lock:
            row = self._connection.execute(
                "SELECT document FROM endpoints WHERE id = ?", (str(endpoint_id),)
            ).fetchone()
        return Endpoint.model_validate_json(row["document"]) if row else None

    def resolve_idempotency(self, key: str | None, digest: str) -> str | None:
        """Resolve replay or reject conflicting key reuse. | 解析幂等重放。"""

        if key is None:
            return None
        with self._lock:
            row = self._connection.execute(
                "SELECT request_hash, resource_id FROM idempotency "
                "WHERE scope = 'create-deployment' AND key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        if row["request_hash"] != digest:
            raise ReactorProductError(
                code="REACTOR_IDEMPOTENCY_CONFLICT",
                title="Idempotency key conflict",
                detail="The Idempotency-Key was already used with a different request body.",
                status=409,
            )
        return str(row["resource_id"])

    def remember_idempotency(self, key: str | None, digest: str, resource_id: UUID) -> None:
        """Persist a create-command resource mapping. | 持久化创建命令资源映射。"""

        if key is None:
            return
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO idempotency(scope, key, request_hash, resource_id) "
                "VALUES ('create-deployment', ?, ?, ?)",
                (key, digest, str(resource_id)),
            )

    def append_deployment_event(
        self,
        deployment_id: UUID,
        phase: DeploymentPhase,
        message: str,
        occurred_at: datetime,
        failure_code: str | None = None,
    ) -> DeploymentEvent:
        """Record an execution phase transition event. | 记录部署阶段事件。"""

        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM deployment_events "
                "WHERE deployment_id = ?",
                (str(deployment_id),),
            ).fetchone()
            seq = int(row[0]) if row else 1
            self._connection.execute(
                """
                INSERT INTO deployment_events (
                    deployment_id, sequence, phase, message, occurred_at, failure_code
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(deployment_id),
                    seq,
                    phase.value if hasattr(phase, "value") else str(phase),
                    message,
                    occurred_at.isoformat(),
                    failure_code,
                ),
            )
            return DeploymentEvent(
                sequence=seq,
                phase=DeploymentPhase(phase),
                message=message,
                occurred_at=occurred_at,
                failure_code=failure_code,
            )

    def append_deployment_diagnostics(
        self, deployment_id: UUID, documents: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        """Append diagnostics with one monotonic sequence per deployment.

        Both Product records and harvested runtime records land in this table so
        a console pages one ordered stream instead of merging two.

            中文:为每个 Deployment 按单调递增序列追加诊断记录。

                中文：Product 记录和收集到的运行时记录都会写入此表,
                使控制台只需分页读取一条有序数据流,而不必合并两个数据流。
        """

        if not documents:
            return []
        appended: list[dict[str, object]] = []
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM deployment_diagnostics"
                " WHERE deployment_id = ?",
                (str(deployment_id),),
            ).fetchone()
            sequence = int(row[0]) if row else 0
            index_row = self._connection.execute(
                "SELECT COUNT(*) FROM deployment_diagnostics WHERE deployment_id = ?",
                (str(deployment_id),),
            ).fetchone()
            record_index = int(index_row[0]) if index_row else 0
            for offset, document in enumerate(documents):
                sequence += 1
                index = record_index + offset
                record = {**document, "sequence": sequence}
                self._connection.execute(
                    "INSERT OR REPLACE INTO deployment_diagnostics"
                    " (deployment_id, record_index, sequence, document) VALUES (?, ?, ?, ?)",
                    (str(deployment_id), index, sequence, json.dumps(record, sort_keys=True)),
                )
                appended.append(record)
        return appended

    def deployment_diagnostics_count(self, deployment_id: UUID) -> int:
        """How many diagnostic records are already durable for a deployment.

        中文:某个 Deployment 已持久化的诊断记录数量。"""

        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) FROM deployment_diagnostics WHERE deployment_id = ?",
                (str(deployment_id),),
            ).fetchone()
        return int(row[0]) if row else 0

    def list_deployment_diagnostics(
        self, deployment_id: UUID, after_sequence: int = 0, limit: int = 200
    ) -> list[dict[str, object]]:
        """Read diagnostics in sequence order. | 按序号读取部署诊断。"""

        bounded = max(1, min(int(limit), 500))
        with self._lock:
            rows = self._connection.execute(
                "SELECT document FROM deployment_diagnostics"
                " WHERE deployment_id = ? AND sequence > ? ORDER BY sequence ASC LIMIT ?",
                (str(deployment_id), int(after_sequence), bounded),
            ).fetchall()
        return [json.loads(row["document"]) for row in rows]

    def deployment_diagnostics_degraded(self, deployment_id: UUID) -> bool:
        """True when a persisted record shows the runtime lost output.

        中文:当持久化记录表明运行时丢失了输出时返回 True。"""

        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM deployment_diagnostics WHERE deployment_id = ? AND document LIKE ?",
                (str(deployment_id), "%REACTOR.DIAGNOSTICS.DEGRADED%"),
            ).fetchone()
        return row is not None

    def runtime_diagnostics_cursor(self, deployment_id: UUID) -> int:
        """Highest runtime sequence already harvested for this deployment.

        中文:此 Deployment 已收集到的最高运行时序列号。"""

        with self._lock:
            row = self._connection.execute(
                "SELECT runtime_sequence FROM deployment_diagnostics_cursors"
                " WHERE deployment_id = ?",
                (str(deployment_id),),
            ).fetchone()
        return int(row["runtime_sequence"]) if row else 0

    def set_runtime_diagnostics_cursor(self, deployment_id: UUID, sequence: int) -> None:
        """Record how much runtime output has been harvested.

        中文:记录已收集的运行时输出量。"""

        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO deployment_diagnostics_cursors"
                " (deployment_id, runtime_sequence) VALUES (?, ?)",
                (str(deployment_id), int(sequence)),
            )

    def list_deployment_events(self, deployment_id: UUID) -> list[DeploymentEvent]:
        """List all events recorded for a deployment in order. | 按序列出部署阶段事件。"""

        with self._lock:
            rows = self._connection.execute(
                """
                SELECT sequence, phase, message, occurred_at, failure_code
                FROM deployment_events
                WHERE deployment_id = ?
                ORDER BY sequence ASC
                """,
                (str(deployment_id),),
            ).fetchall()
            return [
                DeploymentEvent(
                    sequence=row["sequence"],
                    phase=DeploymentPhase(row["phase"]),
                    message=row["message"],
                    occurred_at=datetime.fromisoformat(row["occurred_at"]),
                    failure_code=row["failure_code"],
                )
                for row in rows
            ]
