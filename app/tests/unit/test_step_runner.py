from __future__ import annotations

import threading
from pathlib import Path

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import StepStatus
from app.src.storage.sqlite import SqliteStore
from app.src.workers.step_runner import StepRunner, _get_lock


def test_step_runner_generates_reviewable_artifact(tmp_path: Path) -> None:
    store = SqliteStore(":memory:")
    artifacts = ArtifactStore(str(tmp_path / "artifacts"))
    runner = StepRunner(store=store, artifact_store=artifacts)

    task = store.create_task(video_type="knowledge_share", input_kind="topic", input_text="hello", source_links=[])
    store.init_steps(task.id, ["script_generation"])

    executed = runner.run_step(task_id=task.id, step_key="script_generation")
    assert executed is True

    step = store.get_step(task.id, "script_generation")
    assert step is not None
    assert step.status == StepStatus.completed

    rows = store.list_artifacts(task.id)
    assert any(a.step_key == "script_generation" for a in rows)


def test_step_runner_mutual_exclusion(tmp_path: Path) -> None:
    store = SqliteStore(":memory:")
    artifacts = ArtifactStore(str(tmp_path / "artifacts"))
    runner = StepRunner(store=store, artifact_store=artifacts)

    task = store.create_task(video_type="knowledge_share", input_kind="topic", input_text="hello", source_links=[])
    store.init_steps(task.id, ["script_generation"])

    lock = _get_lock(task.id, "script_generation")
    lock.acquire()
    try:
        executed = runner.run_step(task_id=task.id, step_key="script_generation")
        assert executed is False
    finally:
        lock.release()

