from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CreateVideoTaskRequest(BaseModel):
    input_kind: str = Field(..., examples=["topic", "draft", "article_url"])
    input_text: str
    source_links: list[str] = Field(default_factory=list)


class CreateVideoTaskResponse(BaseModel):
    task_id: str


class StepDTO(BaseModel):
    step_key: str
    status: str
    progress_percent: int = 0
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskDTO(BaseModel):
    id: str
    video_type: str
    status: str
    input_kind: str
    input_text: str
    source_links: list[str]
    created_at: datetime
    updated_at: datetime


class TaskDetailResponse(BaseModel):
    task: TaskDTO
    steps: list[StepDTO]


class ArtifactDTO(BaseModel):
    id: str
    step_key: str
    artifact_type: str
    storage_ref: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactDTO]


class RetryStepRequest(BaseModel):
    step_key: str


class RetryStepResponse(BaseModel):
    accepted: bool


class TaskListItemDTO(BaseModel):
    id: str
    status: str
    input_kind: str
    input_text_summary: str
    created_at: datetime


class TaskListResponse(BaseModel):
    tasks: list[TaskListItemDTO]


class ArtifactContentResponse(BaseModel):
    artifact_id: str
    content: Any


class UploadMaterialResponse(BaseModel):
    accepted: bool
    filename: Optional[str] = None
    artifact_id: Optional[str] = None
