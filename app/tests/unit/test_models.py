from __future__ import annotations

from app.src.domain.models import ArtifactType
from app.src.storage.sqlite import SqliteStore


def test_sqlite_store_create_task_and_artifacts() -> None:
    store = SqliteStore(":memory:")
    task = store.create_task(
        video_type="knowledge_share",
        input_kind="topic",
        input_text="test topic",
        source_links=["https://example.com/video.mp4"],
    )
    assert task.id
    assert task.status.value == "pending"

    steps = store.init_steps(task.id, ["script_generation", "review_script"])
    assert [s.step_key for s in steps] == ["script_generation", "review_script"]

    store.add_artifact(
        task_id=task.id,
        step_key="script_generation",
        artifact_type=ArtifactType.input,
        storage_ref="artifacts/input.json",
        metadata={"k": "v"},
    )
    artifacts = store.list_artifacts(task.id)
    assert len(artifacts) == 1
    assert artifacts[0].artifact_type == ArtifactType.input
    assert artifacts[0].metadata["k"] == "v"

