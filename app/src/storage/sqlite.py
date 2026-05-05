from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from app.src.domain.models import ArtifactType, StepStatus, TaskArtifact, TaskStatus, VideoTask, WorkflowStep


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_parent_dir()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def _ensure_parent_dir(self) -> None:
        if self.db_path == ":memory:":
            return
        Path(self.db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        # Keep a single connection so `:memory:` databases retain schema/data
        # across method calls.
        return self._conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS video_tasks (
                  id TEXT PRIMARY KEY,
                  video_type TEXT NOT NULL,
                  status TEXT NOT NULL,
                  input_kind TEXT NOT NULL,
                  input_text TEXT NOT NULL,
                  source_links_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workflow_steps (
                  task_id TEXT NOT NULL,
                  step_key TEXT NOT NULL,
                  status TEXT NOT NULL,
                  progress_percent INTEGER NOT NULL,
                  error_category TEXT,
                  error_message TEXT,
                  retry_count INTEGER NOT NULL,
                  started_at TEXT,
                  completed_at TEXT,
                  PRIMARY KEY (task_id, step_key),
                  FOREIGN KEY (task_id) REFERENCES video_tasks(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS task_artifacts (
                  id TEXT PRIMARY KEY,
                  task_id TEXT NOT NULL,
                  step_key TEXT NOT NULL,
                  artifact_type TEXT NOT NULL,
                  storage_ref TEXT NOT NULL,
                  metadata_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY (task_id) REFERENCES video_tasks(id) ON DELETE CASCADE
                );
                """
            )

    # --- Tasks
    def create_task(
        self,
        *,
        video_type: str,
        input_kind: str,
        input_text: str,
        source_links: list[str],
    ) -> VideoTask:
        task_id = uuid.uuid4().hex
        now = utc_now()
        task = VideoTask(
            id=task_id,
            video_type=video_type,
            status=TaskStatus.pending,
            input_kind=input_kind,
            input_text=input_text,
            source_links_json=json.dumps(source_links, ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO video_tasks(
                  id, video_type, status, input_kind, input_text, source_links_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.video_type,
                    task.status.value,
                    task.input_kind,
                    task.input_text,
                    task.source_links_json,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                ),
            )
        return task

    def list_tasks(self) -> list[VideoTask]:
        """Return all tasks ordered by created_at DESC."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM video_tasks ORDER BY created_at DESC"
            ).fetchall()
        tasks: list[VideoTask] = []
        for row in rows:
            tasks.append(
                VideoTask(
                    id=row["id"],
                    video_type=row["video_type"],
                    status=TaskStatus(row["status"]),
                    input_kind=row["input_kind"],
                    input_text=row["input_text"],
                    source_links_json=row["source_links_json"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            )
        return tasks

    def set_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update task status and updated_at timestamp."""
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE video_tasks SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now.isoformat(), task_id),
            )

    def get_task(self, task_id: str) -> Optional[VideoTask]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM video_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        return VideoTask(
            id=row["id"],
            video_type=row["video_type"],
            status=TaskStatus(row["status"]),
            input_kind=row["input_kind"],
            input_text=row["input_text"],
            source_links_json=row["source_links_json"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # --- Steps
    def init_steps(self, task_id: str, step_keys: Iterable[str]) -> list[WorkflowStep]:
        now = utc_now()
        steps: list[WorkflowStep] = []
        with self._connect() as conn:
            for key in step_keys:
                step = WorkflowStep(
                    task_id=task_id,
                    step_key=key,
                    status=StepStatus.pending,
                    progress_percent=0,
                    error_category=None,
                    error_message=None,
                    retry_count=0,
                    started_at=None,
                    completed_at=None,
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO workflow_steps(
                      task_id, step_key, status, progress_percent, error_category, error_message, retry_count,
                      started_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        step.task_id,
                        step.step_key,
                        step.status.value,
                        step.progress_percent,
                        step.error_category,
                        step.error_message,
                        step.retry_count,
                        None,
                        None,
                    ),
                )
                steps.append(step)
        return steps

    def list_steps(self, task_id: str) -> list[WorkflowStep]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM workflow_steps WHERE task_id = ? ORDER BY step_key ASC", (task_id,)
            ).fetchall()
        steps: list[WorkflowStep] = []
        for row in rows:
            steps.append(
                WorkflowStep(
                    task_id=row["task_id"],
                    step_key=row["step_key"],
                    status=StepStatus(row["status"]),
                    progress_percent=int(row["progress_percent"]),
                    error_category=row["error_category"],
                    error_message=row["error_message"],
                    retry_count=int(row["retry_count"]),
                    started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                )
            )
        return steps

    def get_step(self, task_id: str, step_key: str) -> Optional[WorkflowStep]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workflow_steps WHERE task_id = ? AND step_key = ?",
                (task_id, step_key),
            ).fetchone()
        if not row:
            return None
        return WorkflowStep(
            task_id=row["task_id"],
            step_key=row["step_key"],
            status=StepStatus(row["status"]),
            progress_percent=int(row["progress_percent"]),
            error_category=row["error_category"],
            error_message=row["error_message"],
            retry_count=int(row["retry_count"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

    def reset_step_for_retry(self, task_id: str, step_key: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_steps
                SET status = ?, progress_percent = 0, error_category = NULL, error_message = NULL,
                    retry_count = retry_count + 1, started_at = NULL, completed_at = NULL
                WHERE task_id = ? AND step_key = ?
                """,
                (StepStatus.pending.value, task_id, step_key),
            )

    def set_step_status(
        self,
        task_id: str,
        step_key: str,
        status: StepStatus,
        *,
        progress_percent: Optional[int] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_steps
                SET status = ?, progress_percent = COALESCE(?, progress_percent)
                WHERE task_id = ? AND step_key = ?
                """,
                (status.value, progress_percent, task_id, step_key),
            )

    def set_step_failed(self, task_id: str, step_key: str, *, error_category: str, error_message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_steps
                SET status = ?, error_category = ?, error_message = ?
                WHERE task_id = ? AND step_key = ?
                """,
                (StepStatus.failed.value, error_category, error_message, task_id, step_key),
            )

    # --- Artifacts
    def add_artifact(
        self,
        *,
        task_id: str,
        step_key: str,
        artifact_type: ArtifactType,
        storage_ref: str,
        metadata: dict[str, Any] | None = None,
    ) -> TaskArtifact:
        artifact_id = uuid.uuid4().hex
        now = utc_now()
        artifact = TaskArtifact(
            id=artifact_id,
            task_id=task_id,
            step_key=step_key,
            artifact_type=artifact_type,
            storage_ref=storage_ref,
            metadata=metadata or {},
            created_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_artifacts(
                  id, task_id, step_key, artifact_type, storage_ref, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.id,
                    artifact.task_id,
                    artifact.step_key,
                    artifact.artifact_type.value,
                    artifact.storage_ref,
                    json.dumps(artifact.metadata, ensure_ascii=False),
                    artifact.created_at.isoformat(),
                ),
            )
        return artifact

    def list_artifacts(self, task_id: str) -> list[TaskArtifact]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM task_artifacts WHERE task_id = ? ORDER BY created_at ASC", (task_id,)
            ).fetchall()
        artifacts: list[TaskArtifact] = []
        for row in rows:
            artifacts.append(
                TaskArtifact(
                    id=row["id"],
                    task_id=row["task_id"],
                    step_key=row["step_key"],
                    artifact_type=ArtifactType(row["artifact_type"]),
                    storage_ref=row["storage_ref"],
                    metadata=json.loads(row["metadata_json"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return artifacts

    def get_artifact(self, task_id: str, artifact_id: str) -> Optional[TaskArtifact]:
        """Return a single artifact by task_id and artifact_id, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM task_artifacts WHERE id = ? AND task_id = ?",
                (artifact_id, task_id),
            ).fetchone()
        if not row:
            return None
        return TaskArtifact(
            id=row["id"],
            task_id=row["task_id"],
            step_key=row["step_key"],
            artifact_type=ArtifactType(row["artifact_type"]),
            storage_ref=row["storage_ref"],
            metadata=json.loads(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )