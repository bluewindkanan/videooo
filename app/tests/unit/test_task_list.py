"""Tests for task list and artifact content endpoints (T005)."""
from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient

from app.src.domain.models import ArtifactType
from app.src.server.main import create_app


def _create_task_directly(app, input_text: str = "test input") -> str:
    """Create a task via store directly (avoids LLM call from the endpoint)."""
    store = app.state.store
    task = store.create_task(
        video_type="knowledge_share",
        input_kind="topic",
        input_text=input_text,
        source_links=[],
    )
    store.init_steps(task.id, ["script_generation", "storyboard", "review_script"])
    return task.id


# ---------------------------------------------------------------------------
# 1. Store-level: SqliteStore.list_tasks()
# ---------------------------------------------------------------------------


def test_store_list_tasks_returns_tasks_in_desc_order() -> None:
    """SqliteStore.list_tasks() returns tasks ordered by created_at DESC."""
    app = create_app(db_path=":memory:")
    store = app.state.store

    t1 = store.create_task(
        video_type="knowledge_share",
        input_kind="topic",
        input_text="first task",
        source_links=[],
    )
    time.sleep(0.05)
    t2 = store.create_task(
        video_type="knowledge_share",
        input_kind="draft",
        input_text="second task",
        source_links=["https://example.com"],
    )

    tasks = store.list_tasks()
    assert len(tasks) == 2
    # DESC order: newest first
    assert tasks[0].id == t2.id
    assert tasks[1].id == t1.id


# ---------------------------------------------------------------------------
# 2. API: GET /api/video-tasks (list)
# ---------------------------------------------------------------------------


def test_list_tasks_endpoint() -> None:
    """GET /api/video-tasks returns all tasks."""
    app = create_app(db_path=":memory:")
    client = TestClient(app)

    tid1 = _create_task_directly(app, input_text="alpha task content")
    tid2 = _create_task_directly(app, input_text="beta task content")

    resp = client.get("/api/video-tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert "tasks" in data
    assert len(data["tasks"]) == 2

    returned_ids = {t["id"] for t in data["tasks"]}
    assert tid1 in returned_ids
    assert tid2 in returned_ids


def test_list_tasks_ordered_by_created_at_desc() -> None:
    """Tasks in list are ordered newest-first."""
    app = create_app(db_path=":memory:")
    client = TestClient(app)

    _create_task_directly(app, input_text="older")
    time.sleep(0.05)
    _create_task_directly(app, input_text="newer")

    resp = client.get("/api/video-tasks")
    assert resp.status_code == 200
    tasks = resp.json()["tasks"]
    assert len(tasks) == 2
    assert tasks[0]["input_text_summary"].startswith("newer")
    assert tasks[1]["input_text_summary"].startswith("older")


def test_list_tasks_input_text_truncated() -> None:
    """input_text_summary is truncated to 80 chars."""
    app = create_app(db_path=":memory:")
    client = TestClient(app)

    long_text = "x" * 200
    _create_task_directly(app, input_text=long_text)

    resp = client.get("/api/video-tasks")
    assert resp.status_code == 200
    task = resp.json()["tasks"][0]
    assert len(task["input_text_summary"]) == 80


# ---------------------------------------------------------------------------
# 3. API: GET /api/video-tasks/{task_id}/artifacts/{artifact_id}/content
# ---------------------------------------------------------------------------


def test_artifact_content_endpoint() -> None:
    """GET .../artifacts/{artifact_id}/content returns the JSON file content."""
    app = create_app(db_path=":memory:")
    client = TestClient(app)
    store = app.state.store
    artifact_store = app.state.artifact_store

    tid = _create_task_directly(app, input_text="check artifact content")

    # Write a test artifact via the artifact store
    payload = {"hook": "test hook", "body": "test body", "call_to_action": "act now", "estimated_duration_seconds": 30}
    ref = artifact_store.write_json(
        task_id=tid,
        step_key="script_generation",
        artifact_type="parsed_json",
        payload=payload,
    )
    store.add_artifact(
        task_id=tid,
        step_key="script_generation",
        artifact_type=ArtifactType.parsed_json,
        storage_ref=ref.storage_ref,
        metadata={"kind": "script_draft"},
    )

    # Get the artifact list to find the artifact ID
    arts_resp = client.get(f"/api/video-tasks/{tid}/artifacts")
    assert arts_resp.status_code == 200
    artifacts = arts_resp.json()["artifacts"]
    assert len(artifacts) >= 1

    artifact_id = artifacts[0]["id"]
    content_resp = client.get(f"/api/video-tasks/{tid}/artifacts/{artifact_id}/content")
    assert content_resp.status_code == 200
    data = content_resp.json()
    assert data["artifact_id"] == artifact_id
    assert data["content"]["hook"] == "test hook"
    assert data["content"]["body"] == "test body"


def test_artifact_content_db_ref() -> None:
    """Artifact with db:// storage_ref returns metadata as content."""
    app = create_app(db_path=":memory:")
    client = TestClient(app)
    store = app.state.store

    tid = _create_task_directly(app, input_text="db ref test")

    # Input artifacts use db:// refs — create one manually
    art = store.add_artifact(
        task_id=tid,
        step_key="input",
        artifact_type=ArtifactType.input,
        storage_ref="db://input",
        metadata={"input_kind": "topic", "input_text": "hello world"},
    )

    content_resp = client.get(f"/api/video-tasks/{tid}/artifacts/{art.id}/content")
    assert content_resp.status_code == 200
    data = content_resp.json()
    assert data["artifact_id"] == art.id
    assert data["content"]["input_kind"] == "topic"
    assert data["content"]["input_text"] == "hello world"


def test_artifact_content_not_found() -> None:
    """GET .../artifacts/{nonexistent}/content returns 404."""
    app = create_app(db_path=":memory:")
    client = TestClient(app)

    tid = _create_task_directly(app, input_text="artifact 404 test")

    fake_artifact_id = "doesnotexist000000000000000000000000"
    resp = client.get(f"/api/video-tasks/{tid}/artifacts/{fake_artifact_id}/content")
    assert resp.status_code == 404


def test_artifact_content_task_not_found() -> None:
    """GET .../artifacts/... for nonexistent task returns 404."""
    app = create_app(db_path=":memory:")
    client = TestClient(app)

    resp = client.get("/api/video-tasks/nonexistent/artifacts/fake/content")
    assert resp.status_code == 404
