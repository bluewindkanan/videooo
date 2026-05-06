from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from typing import Optional


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    needs_review = "needs_review"
    failed = "failed"
    completed = "completed"
    waiting_for_material = "waiting_for_material"


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    failed = "failed"
    completed = "completed"
    skipped = "skipped"


class ArtifactType(str, Enum):
    input = "input"
    llm_raw = "llm_raw"
    parsed_json = "parsed_json"
    review = "review"
    error = "error"
    source_video = "source_video"
    uploaded_video = "uploaded_video"
    material_status = "material_status"
    audio = "audio"
    clip = "clip"
    subtitle = "subtitle"
    final_video = "final_video"


@dataclass(frozen=True)
class VideoTask:
    id: str
    video_type: str
    status: TaskStatus
    input_kind: str
    input_text: str
    source_links_json: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class WorkflowStep:
    task_id: str
    step_key: str
    status: StepStatus
    progress_percent: int
    error_category: Optional[str]
    error_message: Optional[str]
    retry_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


@dataclass(frozen=True)
class TaskArtifact:
    id: str
    task_id: str
    step_key: str
    artifact_type: ArtifactType
    storage_ref: str
    metadata: dict[str, Any]
    created_at: datetime
