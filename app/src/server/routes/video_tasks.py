from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.src.domain.models import ArtifactType, StepStatus, TaskStatus
from app.src.server.schemas import (
    ArtifactContentResponse,
    ArtifactDTO,
    ArtifactListResponse,
    CreateVideoTaskRequest,
    CreateVideoTaskResponse,
    RetryStepRequest,
    RetryStepResponse,
    StepDTO,
    TaskDTO,
    TaskDetailResponse,
    TaskListItemDTO,
    TaskListResponse,
    UploadMaterialResponse,
)

router = APIRouter(prefix="/api/video-tasks", tags=["video-tasks"])


DEFAULT_STEP_KEYS = ["material_fetch", "script_generation", "storyboard", "review_script"]


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

    # Run the pipeline: material_fetch first, then LLM steps if not blocked.
    from app.src.workers.step_runner import StepRunner  # local import to keep server boot minimal

    store.set_task_status(task.id, TaskStatus.running)
    runner = StepRunner(store=store, artifact_store=artifact_store)
    runner.run_step(task_id=task.id, step_key="material_fetch")

    # Check if material_fetch blocked the pipeline
    task = store.get_task(task.id)
    if task and task.status != TaskStatus.waiting_for_material:
        for step_key in ["script_generation", "storyboard", "review_script"]:
            runner.run_step(task_id=task.id, step_key=step_key)

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


@router.get("", response_model=TaskListResponse)
def list_video_tasks(req: Request) -> TaskListResponse:
    """Return all tasks ordered by created_at DESC."""
    store = req.app.state.store
    tasks = store.list_tasks()
    items: list[TaskListItemDTO] = []
    for t in tasks:
        summary = t.input_text[:80]
        items.append(
            TaskListItemDTO(
                id=t.id,
                status=t.status.value,
                input_kind=t.input_kind,
                input_text_summary=summary,
                created_at=t.created_at,
            )
        )
    return TaskListResponse(tasks=items)


@router.get("/{task_id}/artifacts/{artifact_id}/content", response_model=ArtifactContentResponse)
def get_artifact_content(req: Request, task_id: str, artifact_id: str) -> ArtifactContentResponse:
    """Return the JSON content of a specific artifact."""
    store = req.app.state.store
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")

    artifact = store.get_artifact(task_id, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact_not_found")

    storage_ref = artifact.storage_ref
    if storage_ref.startswith("db://"):
        # db:// references store data in metadata
        return ArtifactContentResponse(
            artifact_id=artifact.id,
            content=artifact.metadata,
        )

    file_path = Path(storage_ref)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="artifact_file_not_found")

    # Binary files (video etc.) cannot be returned as JSON content
    binary_extensions = {".mp4", ".mov", ".avi", ".mp3", ".wav", ".png", ".jpg"}
    if file_path.suffix.lower() in binary_extensions:
        return ArtifactContentResponse(
            artifact_id=artifact.id,
            content={"note": "binary_file", "storage_ref": str(file_path), "file_size": file_path.stat().st_size},
        )

    content = json.loads(file_path.read_text(encoding="utf-8"))
    return ArtifactContentResponse(
        artifact_id=artifact.id,
        content=content,
    )


_ALLOWED_UPLOAD_EXTENSIONS = {".mp4", ".mov", ".avi"}
_ALLOWED_UPLOAD_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}
_MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB


@router.post("/{task_id}/materials", response_model=UploadMaterialResponse)
async def upload_material(
    req: Request,
    task_id: str,
    file: UploadFile = File(...),
) -> UploadMaterialResponse:
    """Upload a video file to replace failed source links."""
    store = req.app.state.store
    artifact_store = req.app.state.artifact_store

    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")

    if task.status != TaskStatus.waiting_for_material:
        raise HTTPException(status_code=409, detail="task_not_waiting_for_material")

    # Validate extension
    filename = file.filename or "unknown.mp4"
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"unsupported_file_extension: {ext}")

    # Read content
    content = await file.read()
    if len(content) > _MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=422, detail="file_too_large")

    # Store file
    ref = artifact_store.write_file(
        task_id=task_id,
        step_key="material_fetch",
        artifact_type="uploaded_video",
        filename=filename,
        content=content,
    )
    store.add_artifact(
        task_id=task_id,
        step_key="material_fetch",
        artifact_type=ArtifactType.uploaded_video,
        storage_ref=ref.storage_ref,
        metadata={"upload_filename": filename, "file_size": len(content), "content_type": file.content_type},
    )

    # Mark material_fetch step as completed
    store.set_step_status(task_id, "material_fetch", StepStatus.completed, progress_percent=100)
    store.set_task_status(task_id, TaskStatus.running)

    # Resume pipeline
    from app.src.workers.step_runner import StepRunner

    runner = StepRunner(store=store, artifact_store=artifact_store)
    for step_key in ["script_generation", "storyboard", "review_script"]:
        runner.run_step(task_id=task_id, step_key=step_key)

    return UploadMaterialResponse(accepted=True, filename=filename, artifact_id=ref.storage_ref)
