"""Unit tests for material_extract skill + StepRunner integration."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import ArtifactType, StepStatus
from app.src.storage.sqlite import SqliteStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_MP4_BYTES = b"\x00\x00\x00\x20ftypisom" + b"\x00" * 500


def _make_mock_artifact_store(tmp_path: Path) -> ArtifactStore:
    """Create a real ArtifactStore backed by a temp directory."""
    return ArtifactStore(str(tmp_path / "artifacts"))


def _setup_source_video_artifacts(
    store: SqliteStore,
    artifact_store: ArtifactStore,
    task_id: str,
    refs: list[str],
) -> list[str]:
    """Write fake source_video artifacts and return their storage_refs."""
    storage_refs: list[str] = []
    for ref in refs:
        # Write a dummy file so that _read_latest_artifact_payload can find it
        artifact_ref = artifact_store.write_file(
            task_id=task_id,
            step_key="material_fetch",
            artifact_type="source_video",
            filename="source.mp4",
            content=FAKE_MP4_BYTES,
        )
        store.add_artifact(
            task_id=task_id,
            step_key="material_fetch",
            artifact_type=ArtifactType.source_video,
            storage_ref=artifact_ref.storage_ref,
            metadata={"source_url": ref, "content_type": "video/mp4"},
        )
        storage_refs.append(artifact_ref.storage_ref)
    return storage_refs


# ---------------------------------------------------------------------------
# Test Cases: material_extract skill
# ---------------------------------------------------------------------------


class TestExtractClipsFromSource:
    """1 source video (15s) -> 3 clips with correct manifest."""

    @patch("app.src.skills.material_extract.ffmpeg_utils.run_ffmpeg")
    @patch("app.src.skills.material_extract.ffmpeg_utils.probe_duration")
    @patch("app.src.skills.material_extract.ffmpeg_utils.check_ffmpeg_available")
    def test_extract_clips_from_source(
        self,
        mock_check_ffmpeg: MagicMock,
        mock_probe: MagicMock,
        mock_run_ffmpeg: MagicMock,
        tmp_path: Path,
    ) -> None:
        from app.src.skills.material_extract import run_material_extract

        mock_check_ffmpeg.return_value = (True, "ffmpeg version 6.0")
        mock_probe.return_value = 15.0

        # run_ffmpeg is called for each clip extraction; we need it to create
        # a real temp file with fake MP4 bytes so the skill can read them back.
        def _fake_run_ffmpeg(args: list[str]) -> MagicMock:
            # args ends with the output path
            output_path = args[-1]
            Path(output_path).write_bytes(FAKE_MP4_BYTES)
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        mock_run_ffmpeg.side_effect = _fake_run_ffmpeg

        store = _make_mock_artifact_store(tmp_path)
        source_refs = ["/fake/path/source.mp4"]

        manifest = run_material_extract(
            source_video_refs=source_refs,
            artifact_store=store,
            task_id="task-001",
        )

        # Verify manifest structure
        assert "clips" in manifest
        assert len(manifest["clips"]) == 3  # ceil(15/5) = 3
        assert manifest["total_clip_duration_seconds"] == 15.0

        # Verify per-clip structure
        for i, clip in enumerate(manifest["clips"]):
            assert clip["clip_index"] == i
            assert clip["source_ref"] == "/fake/path/source.mp4"
            assert clip["start_seconds"] == i * 5.0
            assert clip["end_seconds"] == min((i + 1) * 5.0, 15.0)
            assert clip["duration_seconds"] == 5.0 if i < 2 else 5.0
            assert "storage_ref" in clip
            assert clip["storage_ref"].endswith(".mp4")


class TestExtractNoSourceVideos:
    """Empty source_video_refs -> empty manifest."""

    def test_extract_no_source_videos(self, tmp_path: Path) -> None:
        from app.src.skills.material_extract import run_material_extract

        store = _make_mock_artifact_store(tmp_path)
        manifest = run_material_extract(
            source_video_refs=[],
            artifact_store=store,
            task_id="task-002",
        )

        assert manifest["clips"] == []
        assert manifest["total_clip_duration_seconds"] == 0.0


class TestExtractFFmpegNotAvailable:
    """FFmpeg not available raises MaterialExtractError."""

    @patch("app.src.skills.material_extract.ffmpeg_utils.check_ffmpeg_available")
    def test_extract_ffmpeg_not_available(
        self,
        mock_check_ffmpeg: MagicMock,
        tmp_path: Path,
    ) -> None:
        from app.src.skills.material_extract import MaterialExtractError, run_material_extract

        mock_check_ffmpeg.return_value = (False, "FFmpeg not found")

        store = _make_mock_artifact_store(tmp_path)

        with pytest.raises(MaterialExtractError):
            run_material_extract(
                source_video_refs=["/fake/video.mp4"],
                artifact_store=store,
                task_id="task-003",
            )


class TestExtractClipDurationConfigurable:
    """Verify clips are ~5s each for a 23s source -> 5 clips."""

    @patch("app.src.skills.material_extract.ffmpeg_utils.run_ffmpeg")
    @patch("app.src.skills.material_extract.ffmpeg_utils.probe_duration")
    @patch("app.src.skills.material_extract.ffmpeg_utils.check_ffmpeg_available")
    def test_clip_duration_5s(
        self,
        mock_check_ffmpeg: MagicMock,
        mock_probe: MagicMock,
        mock_run_ffmpeg: MagicMock,
        tmp_path: Path,
    ) -> None:
        from app.src.skills.material_extract import run_material_extract

        mock_check_ffmpeg.return_value = (True, "ffmpeg version 6.0")
        mock_probe.return_value = 23.0

        def _fake_run_ffmpeg(args: list[str]) -> MagicMock:
            output_path = args[-1]
            Path(output_path).write_bytes(FAKE_MP4_BYTES)
            result = MagicMock()
            result.returncode = 0
            return result

        mock_run_ffmpeg.side_effect = _fake_run_ffmpeg

        store = _make_mock_artifact_store(tmp_path)
        manifest = run_material_extract(
            source_video_refs=["/fake/source.mp4"],
            artifact_store=store,
            task_id="task-004",
        )

        assert len(manifest["clips"]) == 5  # ceil(23/5) = 5
        # First 4 clips should be 5s each, last clip 3s
        for clip in manifest["clips"][:4]:
            assert clip["duration_seconds"] == 5.0
        assert manifest["clips"][4]["duration_seconds"] == 3.0
        assert manifest["clips"][4]["start_seconds"] == 20.0
        assert manifest["clips"][4]["end_seconds"] == 23.0
        assert manifest["total_clip_duration_seconds"] == 23.0


# ---------------------------------------------------------------------------
# Test Cases: StepRunner integration
# ---------------------------------------------------------------------------


class TestStepRunnerMaterialExtract:
    """Verify StepRunner dispatches material_extract correctly."""

    @patch("app.src.skills.material_extract.ffmpeg_utils.run_ffmpeg")
    @patch("app.src.skills.material_extract.ffmpeg_utils.probe_duration")
    @patch("app.src.skills.material_extract.ffmpeg_utils.check_ffmpeg_available")
    def test_step_runner_material_extract(
        self,
        mock_check_ffmpeg: MagicMock,
        mock_probe: MagicMock,
        mock_run_ffmpeg: MagicMock,
        tmp_path: Path,
    ) -> None:
        from app.src.workers.step_runner import StepRunner

        mock_check_ffmpeg.return_value = (True, "ffmpeg version 6.0")
        mock_probe.return_value = 10.0

        def _fake_run_ffmpeg(args: list[str]) -> MagicMock:
            output_path = args[-1]
            Path(output_path).write_bytes(FAKE_MP4_BYTES)
            result = MagicMock()
            result.returncode = 0
            return result

        mock_run_ffmpeg.side_effect = _fake_run_ffmpeg

        store = SqliteStore(":memory:")
        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        runner = StepRunner(store=store, artifact_store=artifact_store)

        task = store.create_task(
            video_type="knowledge_share",
            input_kind="topic",
            input_text="test",
            source_links=["https://example.com/source.mp4"],
        )
        store.init_steps(task.id, ["material_fetch", "material_extract"])

        # Create a source_video artifact from material_fetch step
        ref = artifact_store.write_file(
            task_id=task.id,
            step_key="material_fetch",
            artifact_type="source_video",
            filename="source.mp4",
            content=FAKE_MP4_BYTES,
        )
        store.add_artifact(
            task_id=task.id,
            step_key="material_fetch",
            artifact_type=ArtifactType.source_video,
            storage_ref=ref.storage_ref,
            metadata={"source_url": "https://example.com/source.mp4"},
        )

        # Run material_extract step
        executed = runner.run_step(task_id=task.id, step_key="material_extract")
        assert executed is True

        step = store.get_step(task.id, "material_extract")
        assert step is not None
        assert step.status == StepStatus.completed

        # Verify clip artifacts were registered (2 clips for 10s source)
        artifacts = store.list_artifacts(task.id)
        clip_artifacts = [
            a for a in artifacts
            if a.step_key == "material_extract" and a.artifact_type == ArtifactType.clip
        ]
        assert len(clip_artifacts) == 2

        # Verify manifest artifact was registered
        manifest_artifacts = [
            a for a in artifacts
            if a.step_key == "material_extract" and a.artifact_type == ArtifactType.parsed_json
        ]
        assert len(manifest_artifacts) == 1


class TestStepRunnerMaterialExtractSkillRegistered:
    """Verify 'material_extract' is registered in STEP_SKILLS."""

    def test_skill_registered(self) -> None:
        from app.src.workers.step_runner import STEP_SKILLS

        assert "material_extract" in STEP_SKILLS
