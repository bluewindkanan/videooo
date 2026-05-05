"""Feature 003: test new enum values for material dual-path."""
from __future__ import annotations

from app.src.domain.models import ArtifactType, TaskStatus


def test_task_status_waiting_for_material_exists() -> None:
    assert hasattr(TaskStatus, "waiting_for_material")
    assert TaskStatus.waiting_for_material.value == "waiting_for_material"


def test_artifact_type_source_video_exists() -> None:
    assert hasattr(ArtifactType, "source_video")
    assert ArtifactType.source_video.value == "source_video"


def test_artifact_type_uploaded_video_exists() -> None:
    assert hasattr(ArtifactType, "uploaded_video")
    assert ArtifactType.uploaded_video.value == "uploaded_video"


def test_artifact_type_material_status_exists() -> None:
    assert hasattr(ArtifactType, "material_status")
    assert ArtifactType.material_status.value == "material_status"


def test_existing_enum_values_unchanged() -> None:
    """Guard: existing values must not shift."""
    assert TaskStatus.pending.value == "pending"
    assert TaskStatus.running.value == "running"
    assert TaskStatus.completed.value == "completed"
    assert TaskStatus.failed.value == "failed"
    assert TaskStatus.needs_review.value == "needs_review"

    assert ArtifactType.input.value == "input"
    assert ArtifactType.llm_raw.value == "llm_raw"
    assert ArtifactType.parsed_json.value == "parsed_json"
    assert ArtifactType.review.value == "review"
    assert ArtifactType.error.value == "error"
