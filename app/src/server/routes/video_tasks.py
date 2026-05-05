from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

from app.src.domain.models import ArtifactType, StepStatus
from app.src.server.schemas import (
    ArtifactDTO,
    ArtifactListResponse,
    CreateVideoTaskRequest,
    CreateVideoTaskResponse,
    RetryStepRequest,
    RetryStepResponse,
    StepDTO,
    TaskDTO,
    TaskDetailResponse,
)

router = APIRouter(prefix="/api/video-tasks", tags=["video-tasks"])


DEFAULT_STEP_KEYS = ["script_generation", "review_script"]


@router.post("", response_model=CreateVideoTaskResponse)
def create_video_task(req: Request, body: CreateVideoTaskRequest) -> CreateVideoTaskResponse:
    store = req.app.state.store
    artifact_store = req.app.state.artifact_store
    task = store.create_task(
        video_type="knowledge_share",
        input_kind=body.input_kind,
        input_text=body.input_text,
        source_links=body.source_links,
    )
    store.init_steps(task.id, DEFAULT_STEP_KEYS)

    # Artifact-first: persist normalized input as an artifact reference.
    store.add_artifact(
        task_id=task.id,
        step_key="input",
        artifact_type=ArtifactType.input,
        storage_ref="db://input",
        metadata={
            "input_kind": body.input_kind,
            "input_text": body.input_text,
            "source_links": body.source_links,
        },
    )

    # Run the first step immediately for the first slice to guarantee at least
    # one reviewable artifact exists for S-001.
    from app.src.workers.step_runner import StepRunner  # local import to keep server boot minimal

    StepRunner(store=store, artifact_store=artifact_store).run_step(task_id=task.id, step_key="script_generation")
    return CreateVideoTaskResponse(task_id=task.id)


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_video_task(req: Request, task_id: str) -> TaskDetailResponse:
    store = req.app.state.store
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    steps = store.list_steps(task_id)

    return TaskDetailResponse(
        task=TaskDTO(
            id=task.id,
            video_type=task.video_type,
            status=task.status.value,
            input_kind=task.input_kind,
            input_text=task.input_text,
            source_links=json.loads(task.source_links_json),
            created_at=task.created_at,
            updated_at=task.updated_at,
        ),
        steps=[
            StepDTO(
                step_key=s.step_key,
                status=s.status.value,
                progress_percent=s.progress_percent,
                error_category=s.error_category,
                error_message=s.error_message,
                retry_count=s.retry_count,
                started_at=s.started_at,
                completed_at=s.completed_at,
            )
            for s in steps
        ],
    )


@router.get("/{task_id}/artifacts", response_model=ArtifactListResponse)
def list_task_artifacts(req: Request, task_id: str) -> ArtifactListResponse:
    store = req.app.state.store
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    artifacts = store.list_artifacts(task_id)
    return ArtifactListResponse(
        artifacts=[
            ArtifactDTO(
                id=a.id,
                step_key=a.step_key,
                artifact_type=a.artifact_type.value,
                storage_ref=a.storage_ref,
                metadata=a.metadata,
                created_at=a.created_at,
            )
            for a in artifacts
        ]
    )


@router.post("/{task_id}/retry", response_model=RetryStepResponse)
def retry_step(req: Request, task_id: str, body: RetryStepRequest) -> RetryStepResponse:
    store = req.app.state.store
    artifact_store = req.app.state.artifact_store
    step = store.get_step(task_id, body.step_key)
    if not step:
        raise HTTPException(status_code=404, detail="step_not_found")

    if step.status != StepStatus.failed:
        return RetryStepResponse(accepted=False)

    store.reset_step_for_retry(task_id, body.step_key)
    from app.src.workers.step_runner import StepRunner  # local import

    StepRunner(store=store, artifact_store=artifact_store).run_step(task_id=task_id, step_key=body.step_key)
    return RetryStepResponse(accepted=True)
