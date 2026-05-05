from __future__ import annotations

import threading
from typing import Optional

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import ArtifactType, StepStatus
from app.src.storage.sqlite import SqliteStore


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_key(task_id: str, step_key: str) -> str:
    return f"{task_id}:{step_key}"


def _get_lock(task_id: str, step_key: str) -> threading.Lock:
    key = _lock_key(task_id, step_key)
    with _locks_guard:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


class StepRunner:
    def __init__(self, *, store: SqliteStore, artifact_store: ArtifactStore) -> None:
        self.store = store
        self.artifacts = artifact_store

    def run_step(self, *, task_id: str, step_key: str) -> bool:
        """Run a step once. Returns True if executed, False if skipped (e.g., locked)."""
        lock = _get_lock(task_id, step_key)
        if not lock.acquire(blocking=False):
            return False
        try:
            step = self.store.get_step(task_id, step_key)
            if not step:
                return False

            self.store.set_step_status(task_id, step_key, StepStatus.running)

            task = self.store.get_task(task_id)
            if not task:
                self.store.set_step_failed(
                    task_id, step_key, error_category="non_retryable", error_message="task_not_found"
                )
                return True

            # Deterministic placeholder behavior for the first slice.
            input_text = task.input_text or ""
            # Deterministic failure injection for S-002 smoke: first attempt fails when input contains FAIL,
            # second attempt (after retry) succeeds.
            if "FAIL" in input_text.upper() and step.retry_count == 0:
                self.store.set_step_failed(
                    task_id,
                    step_key,
                    error_category="needs_user_action",
                    error_message="simulated failure (contains FAIL)",
                )
                return True

            if step_key == "script_generation":
                draft = {
                    "hook": f"关于：{input_text}",
                    "body": f"要点：{input_text}（占位脚本）",
                    "call_to_action": "关注获取更多干货",
                    "estimated_duration_seconds": 30,
                }
                ref = self.artifacts.write_json(
                    task_id=task_id,
                    step_key=step_key,
                    artifact_type="script_draft",
                    payload=draft,
                )
                self.store.add_artifact(
                    task_id=task_id,
                    step_key=step_key,
                    artifact_type=ArtifactType.parsed_json,
                    storage_ref=ref.storage_ref,
                    metadata={"kind": "script_draft"},
                )
                self.store.set_step_status(task_id, step_key, StepStatus.completed, progress_percent=100)
                return True

            if step_key == "review_script":
                findings = [
                    {
                        "stage": "script",
                        "severity": "info",
                        "location_ref": "hook",
                        "message": "占位 reviewer 结果：暂无明显问题",
                        "suggested_fix": "",
                    }
                ]
                ref = self.artifacts.write_json(
                    task_id=task_id,
                    step_key=step_key,
                    artifact_type="review_findings",
                    payload=findings,
                )
                self.store.add_artifact(
                    task_id=task_id,
                    step_key=step_key,
                    artifact_type=ArtifactType.review,
                    storage_ref=ref.storage_ref,
                    metadata={"kind": "review_findings"},
                )
                self.store.set_step_status(task_id, step_key, StepStatus.completed, progress_percent=100)
                return True

            self.store.set_step_failed(
                task_id,
                step_key,
                error_category="non_retryable",
                error_message=f"unknown_step_key:{step_key}",
            )
            return True
        finally:
            lock.release()
