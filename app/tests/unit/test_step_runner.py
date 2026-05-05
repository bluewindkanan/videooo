from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import MagicMock

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import StepStatus
from app.src.storage.sqlite import SqliteStore
from app.src.workers.step_runner import StepRunner, _get_lock


def _mock_llm_adapter() -> MagicMock:
    """Create a mock LLMAdapter returning valid script JSON."""
    adapter = MagicMock()
    adapter.chat.return_value = json.dumps({
        "hook": "Test hook",
        "body": "Test body",
        "call_to_action": "Test CTA",
        "estimated_duration_seconds": 30,
    })
    return adapter


def test_step_runner_generates_reviewable_artifact(tmp_path: Path) -> None:
    store = SqliteStore(":memory:")
    artifacts = ArtifactStore(str(tmp_path / "artifacts"))
    mock_adapter = _mock_llm_adapter()
    runner = StepRunner(store=store, artifact_store=artifacts, llm_adapter=mock_adapter)

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
    mock_adapter = _mock_llm_adapter()
    runner = StepRunner(store=store, artifact_store=artifacts, llm_adapter=mock_adapter)

    task = store.create_task(video_type="knowledge_share", input_kind="topic", input_text="hello", source_links=[])
    store.init_steps(task.id, ["script_generation"])

    lock = _get_lock(task.id, "script_generation")
    lock.acquire()
    try:
        executed = runner.run_step(task_id=task.id, step_key="script_generation")
        assert executed is False
    finally:
        lock.release()
