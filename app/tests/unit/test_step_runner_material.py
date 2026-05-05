"""Feature 003: test StepRunner material_fetch integration + pipeline ordering."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import ArtifactType, StepStatus, TaskStatus
from app.src.skills.material_fetch import MaterialFetchResult
from app.src.storage.sqlite import SqliteStore
from app.src.workers.step_runner import StepRunner


def _make_runner(tmp_path: Path) -> tuple[SqliteStore, ArtifactStore, StepRunner]:
    store = SqliteStore(":memory:")
    artifacts = ArtifactStore(str(tmp_path / "artifacts"))
    mock_adapter = MagicMock()
    mock_adapter.chat.return_value = json.dumps({
        "hook": "h", "body": "b", "call_to_action": "c", "estimated_duration_seconds": 10,
    })
    runner = StepRunner(store=store, artifact_store=artifacts, llm_adapter=mock_adapter)
    return store, artifacts, runner


class TestMaterialFetchStepDispatch:
    def test_material_fetch_dispatches_to_skill(self, tmp_path: Path) -> None:
        store, artifacts, runner = _make_runner(tmp_path)
        task = store.create_task(
            video_type="knowledge_share", input_kind="topic",
            input_text="test", source_links=["https://example.com/video.mp4"],
        )
        store.init_steps(task.id, ["material_fetch"])

        with patch("app.src.skills.material_fetch.httpx.Client") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.headers = {"content-type": "video/mp4", "content-length": "100"}
            mock_resp.content = b"\x00" * 100
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(get=MagicMock(return_value=mock_resp)))
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            executed = runner.run_step(task_id=task.id, step_key="material_fetch")

        assert executed is True
        step = store.get_step(task.id, "material_fetch")
        assert step is not None
        assert step.status == StepStatus.completed

    def test_material_fetch_all_failed_sets_waiting(self, tmp_path: Path) -> None:
        store, artifacts, runner = _make_runner(tmp_path)
        task = store.create_task(
            video_type="knowledge_share", input_kind="topic",
            input_text="test", source_links=["https://unreachable.example.com/video.mp4"],
        )
        store.init_steps(task.id, ["material_fetch"])

        with patch("app.src.skills.material_fetch.httpx.Client") as mock_client_cls:
            import httpx
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("DNS failure")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            executed = runner.run_step(task_id=task.id, step_key="material_fetch")

        assert executed is True
        step = store.get_step(task.id, "material_fetch")
        assert step is not None
        assert step.status == StepStatus.failed

        task_after = store.get_task(task.id)
        assert task_after is not None
        assert task_after.status == TaskStatus.waiting_for_material

    def test_material_fetch_empty_links_completes(self, tmp_path: Path) -> None:
        store, artifacts, runner = _make_runner(tmp_path)
        task = store.create_task(
            video_type="knowledge_share", input_kind="topic",
            input_text="test", source_links=[],
        )
        store.init_steps(task.id, ["material_fetch"])

        executed = runner.run_step(task_id=task.id, step_key="material_fetch")
        assert executed is True

        step = store.get_step(task.id, "material_fetch")
        assert step is not None
        assert step.status == StepStatus.completed

    def test_material_fetch_writes_status_artifact(self, tmp_path: Path) -> None:
        store, artifacts, runner = _make_runner(tmp_path)
        task = store.create_task(
            video_type="knowledge_share", input_kind="topic",
            input_text="test", source_links=["https://example.com/video.mp4"],
        )
        store.init_steps(task.id, ["material_fetch"])

        with patch("app.src.skills.material_fetch.httpx.Client") as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.headers = {"content-type": "video/mp4", "content-length": "50"}
            mock_resp.content = b"\x00" * 50
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(get=MagicMock(return_value=mock_resp)))
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            runner.run_step(task_id=task.id, step_key="material_fetch")

        arts = store.list_artifacts(task.id)
        status_arts = [a for a in arts if a.artifact_type == ArtifactType.material_status]
        assert len(status_arts) >= 1

    def test_material_fetch_partial_success_completes(self, tmp_path: Path) -> None:
        store, artifacts, runner = _make_runner(tmp_path)
        task = store.create_task(
            video_type="knowledge_share", input_kind="topic",
            input_text="test",
            source_links=["https://example.com/good.mp4", "https://bad.example.com/fail.mp4"],
        )
        store.init_steps(task.id, ["material_fetch"])

        import httpx
        with patch("app.src.skills.material_fetch.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            good_resp = MagicMock()
            good_resp.headers = {"content-type": "video/mp4", "content-length": "100"}
            good_resp.content = b"\x00" * 100
            mock_client.get.side_effect = [good_resp, httpx.ConnectError("fail")]
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            runner.run_step(task_id=task.id, step_key="material_fetch")

        step = store.get_step(task.id, "material_fetch")
        assert step is not None
        assert step.status == StepStatus.completed

        task_after = store.get_task(task.id)
        assert task_after is not None
        assert task_after.status != TaskStatus.waiting_for_material
