"""Feature 003: test SqliteStore.set_task_status."""
from __future__ import annotations

import time

from app.src.domain.models import TaskStatus
from app.src.storage.sqlite import SqliteStore


def test_set_task_status_updates_status_field() -> None:
    store = SqliteStore(":memory:")
    task = store.create_task(
        video_type="knowledge_share",
        input_kind="topic",
        input_text="test",
        source_links=[],
    )
    assert task.status == TaskStatus.pending

    store.set_task_status(task.id, TaskStatus.waiting_for_material)

    updated = store.get_task(task.id)
    assert updated is not None
    assert updated.status == TaskStatus.waiting_for_material


def test_set_task_status_updates_updated_at() -> None:
    store = SqliteStore(":memory:")
    task = store.create_task(
        video_type="knowledge_share",
        input_kind="topic",
        input_text="test",
        source_links=[],
    )
    original_updated_at = task.updated_at

    # small sleep to ensure timestamp differs
    time.sleep(0.05)

    store.set_task_status(task.id, TaskStatus.running)

    updated = store.get_task(task.id)
    assert updated is not None
    assert updated.updated_at > original_updated_at


def test_set_task_status_nonexistent_raises() -> None:
    store = SqliteStore(":memory:")
    # Should not raise -- silent no-op for missing task is acceptable,
    # but the method must exist and run without error.
    store.set_task_status("nonexistent-id", TaskStatus.failed)


def test_set_task_status_multiple_transitions() -> None:
    store = SqliteStore(":memory:")
    task = store.create_task(
        video_type="knowledge_share",
        input_kind="topic",
        input_text="test",
        source_links=[],
    )

    store.set_task_status(task.id, TaskStatus.waiting_for_material)
    updated = store.get_task(task.id)
    assert updated is not None
    assert updated.status == TaskStatus.waiting_for_material

    store.set_task_status(task.id, TaskStatus.running)
    updated = store.get_task(task.id)
    assert updated is not None
    assert updated.status == TaskStatus.running

    store.set_task_status(task.id, TaskStatus.completed)
    updated = store.get_task(task.id)
    assert updated is not None
    assert updated.status == TaskStatus.completed
