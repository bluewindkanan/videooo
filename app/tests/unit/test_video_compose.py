"""Feature 004 T006: Video compose skill + StepRunner integration tests."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import ArtifactType, StepStatus
from app.src.storage.sqlite import SqliteStore
from app.src.workers.step_runner import STEP_SKILLS, StepRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_matched_segments(
    *,
    fallback_mode: bool = False,
    num_matches: int = 2,
) -> dict[str, Any]:
    """Build a matched_segments dict matching T004 output schema."""
    matches: list[dict[str, Any]] = []
    for i in range(num_matches):
        matches.append({
            "segment_index": i,
            "voiceover_duration": 5.0,
            "assigned_clips": [
                {
                    "clip_index": i,
                    "start_seconds": 0.0,
                    "end_seconds": 5.0,
                    "duration_used": 5.0,
                }
            ],
        })
    return {"matches": matches, "fallback_mode": fallback_mode}


def _make_voiceover_timing(
    *,
    total_duration: float = 30.5,
    full_audio_ref: str = "/fake/full_voiceover.mp3",
) -> dict[str, Any]:
    """Build a voiceover_timing dict matching T002 output schema."""
    return {
        "segments": [
            {"segment_index": 0, "duration_seconds": 5.0, "voiceover_text": "Hello"},
            {"segment_index": 1, "duration_seconds": 5.0, "voiceover_text": "World"},
        ],
        "total_duration_seconds": total_duration,
        "full_audio_ref": full_audio_ref,
    }


def _make_clip_manifest(
    *,
    num_clips: int = 2,
) -> dict[str, Any]:
    """Build a clip_manifest dict matching T003 output schema."""
    clips: list[dict[str, Any]] = []
    for i in range(num_clips):
        clips.append({
            "clip_index": i,
            "storage_ref": f"/fake/clip_{i}.mp4",
            "duration_seconds": 5.0,
            "source_ref": "/fake/source.mp4",
            "start_seconds": 0.0,
            "end_seconds": 5.0,
        })
    return {"clips": clips}


def _make_subtitlesrt(tmp_path: Path) -> str:
    """Create a fake .srt file and return its path."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    srt_path = tmp_path / "subs.srt"
    srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:05,000\nHello\n\n2\n00:00:05,000 --> 00:00:10,000\nWorld\n",
        encoding="utf-8",
    )
    return str(srt_path)


def _setup_runner(tmp_path: Path) -> tuple[SqliteStore, ArtifactStore, StepRunner]:
    store = SqliteStore(":memory:")
    artifacts = ArtifactStore(str(tmp_path / "artifacts"))
    mock_adapter = MagicMock()
    runner = StepRunner(store=store, artifact_store=artifacts, llm_adapter=mock_adapter)
    return store, artifacts, runner


# ---------------------------------------------------------------------------
# Test 1: Normal mode — clips available
# ---------------------------------------------------------------------------

class TestComposeNormalMode:
    def test_compose_normal_mode(self, tmp_path: Path) -> None:
        """Normal mode uses concat input with clip files."""
        from app.src.skills.video_compose import run_video_compose

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        matched_segments = _make_matched_segments(fallback_mode=False, num_matches=2)
        voiceover_timing = _make_voiceover_timing()
        clip_manifest = _make_clip_manifest(num_clips=2)
        subtitle_ref = _make_subtitlesrt(tmp_path)

        mock_artifact_store = MagicMock()
        fake_ref = MagicMock()
        fake_ref.storage_ref = "/fake/output.mp4"
        mock_artifact_store.write_file.return_value = fake_ref

        with patch("app.src.skills.video_compose.check_ffmpeg_available", return_value=(True, "ffmpeg version 6")), \
             patch("app.src.skills.video_compose.run_ffmpeg") as mock_ffmpeg:

            # Simulate ffmpeg writing output to a temp file
            def _fake_ffmpeg(args: list[str]) -> MagicMock:
                # Find output_path: last arg
                output_path = args[-1]
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(b"\x00\x00\x00 ftypisom")
                return MagicMock(returncode=0)

            mock_ffmpeg.side_effect = _fake_ffmpeg

            result = run_video_compose(
                matched_segments=matched_segments,
                voiceover_timing=voiceover_timing,
                subtitle_ref=subtitle_ref,
                clip_manifest=clip_manifest,
                artifact_store=mock_artifact_store,
                task_id="test-normal",
            )

        # Verify FFmpeg was called
        assert mock_ffmpeg.called
        call_args = mock_ffmpeg.call_args[0][0]
        # Should use concat demuxer
        assert "-f" in call_args
        concat_idx = call_args.index("-f")
        assert call_args[concat_idx + 1] == "concat"

        # Verify result structure
        assert result["fallback_mode"] is False
        assert result["has_audio"] is True
        assert result["has_subtitles"] is True
        assert result["has_visual"] is True
        assert result["duration_seconds"] == 30.5
        assert result["resolution"] == "1280x720"


# ---------------------------------------------------------------------------
# Test 2: Fallback mode — no clips
# ---------------------------------------------------------------------------

class TestComposeFallbackMode:
    def test_compose_fallback_mode(self, tmp_path: Path) -> None:
        """Fallback mode uses color source instead of clip concat."""
        from app.src.skills.video_compose import run_video_compose

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        matched_segments = _make_matched_segments(fallback_mode=True, num_matches=2)
        voiceover_timing = _make_voiceover_timing()
        clip_manifest = _make_clip_manifest(num_clips=0)
        subtitle_ref = _make_subtitlesrt(tmp_path)

        mock_artifact_store = MagicMock()
        fake_ref = MagicMock()
        fake_ref.storage_ref = "/fake/output.mp4"
        mock_artifact_store.write_file.return_value = fake_ref

        with patch("app.src.skills.video_compose.check_ffmpeg_available", return_value=(True, "ffmpeg version 6")), \
             patch("app.src.skills.video_compose.run_ffmpeg") as mock_ffmpeg:

            def _fake_ffmpeg(args: list[str]) -> MagicMock:
                output_path = args[-1]
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(b"\x00\x00\x00 ftypisom")
                return MagicMock(returncode=0)

            mock_ffmpeg.side_effect = _fake_ffmpeg

            result = run_video_compose(
                matched_segments=matched_segments,
                voiceover_timing=voiceover_timing,
                subtitle_ref=subtitle_ref,
                clip_manifest=clip_manifest,
                artifact_store=mock_artifact_store,
                task_id="test-fallback",
            )

        assert mock_ffmpeg.called
        call_args = mock_ffmpeg.call_args[0][0]

        # Should use lavfi (color source), NOT concat
        assert "-f" in call_args
        f_idx = call_args.index("-f")
        assert call_args[f_idx + 1] == "lavfi"

        # Should contain color source specification
        assert any("color=" in str(a) for a in call_args)

        # Verify result structure
        assert result["fallback_mode"] is True
        assert result["has_visual"] is False
        assert result["has_audio"] is True
        assert result["has_subtitles"] is True


# ---------------------------------------------------------------------------
# Test 3: FFmpeg not available
# ---------------------------------------------------------------------------

class TestComposeFFmpegNotAvailable:
    def test_compose_ffmpeg_not_available(self, tmp_path: Path) -> None:
        """Raise VideoComposeError when FFmpeg is not available."""
        from app.src.skills.video_compose import VideoComposeError, run_video_compose

        mock_artifact_store = MagicMock()

        with patch("app.src.skills.video_compose.check_ffmpeg_available", return_value=(False, "FFmpeg not found")):
            with pytest.raises(VideoComposeError):
                run_video_compose(
                    matched_segments=_make_matched_segments(),
                    voiceover_timing=_make_voiceover_timing(),
                    subtitle_ref=_make_subtitlesrt(tmp_path),
                    clip_manifest=_make_clip_manifest(),
                    artifact_store=mock_artifact_store,
                    task_id="test-no-ffmpeg",
                )


# ---------------------------------------------------------------------------
# Test 4: FFmpeg fails
# ---------------------------------------------------------------------------

class TestComposeFFmpegFails:
    def test_compose_ffmpeg_fails(self, tmp_path: Path) -> None:
        """Raise VideoComposeError when FFmpeg command fails."""
        from app.src.skills.video_compose import VideoComposeError, run_video_compose

        mock_artifact_store = MagicMock()

        with patch("app.src.skills.video_compose.check_ffmpeg_available", return_value=(True, "ffmpeg version 6")), \
             patch("app.src.skills.video_compose.run_ffmpeg", side_effect=RuntimeError("FFmpeg failed")):
            with pytest.raises(VideoComposeError):
                run_video_compose(
                    matched_segments=_make_matched_segments(),
                    voiceover_timing=_make_voiceover_timing(),
                    subtitle_ref=_make_subtitlesrt(tmp_path),
                    clip_manifest=_make_clip_manifest(),
                    artifact_store=mock_artifact_store,
                    task_id="test-ffmpeg-fail",
                )


# ---------------------------------------------------------------------------
# Test 5: Output written via artifact_store
# ---------------------------------------------------------------------------

class TestComposeOutputWritten:
    def test_compose_output_written(self, tmp_path: Path) -> None:
        """Verify output.mp4 is written via artifact_store.write_file."""
        from app.src.skills.video_compose import run_video_compose

        mock_artifact_store = MagicMock()
        fake_ref = MagicMock()
        fake_ref.storage_ref = "/fake/output.mp4"
        mock_artifact_store.write_file.return_value = fake_ref

        with patch("app.src.skills.video_compose.check_ffmpeg_available", return_value=(True, "ffmpeg version 6")), \
             patch("app.src.skills.video_compose.run_ffmpeg") as mock_ffmpeg:

            def _fake_ffmpeg(args: list[str]) -> MagicMock:
                output_path = args[-1]
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(b"\x00\x00\x00 ftypisom")
                return MagicMock(returncode=0)

            mock_ffmpeg.side_effect = _fake_ffmpeg

            result = run_video_compose(
                matched_segments=_make_matched_segments(),
                voiceover_timing=_make_voiceover_timing(),
                subtitle_ref=_make_subtitlesrt(tmp_path),
                clip_manifest=_make_clip_manifest(),
                artifact_store=mock_artifact_store,
                task_id="test-output",
            )

        # Verify write_file was called with .mp4 extension
        mock_artifact_store.write_file.assert_called_once()
        call_kwargs = mock_artifact_store.write_file.call_args[1]
        assert call_kwargs["filename"].endswith(".mp4")
        assert call_kwargs["task_id"] == "test-output"
        assert call_kwargs["step_key"] == "video_compose"

        # Result should contain the storage ref
        assert result["storage_ref"] == "/fake/output.mp4"


# ---------------------------------------------------------------------------
# Test 6: Concat file built correctly
# ---------------------------------------------------------------------------

class TestComposeConcatFileBuilt:
    def test_compose_concat_file_built(self, tmp_path: Path) -> None:
        """Verify concat input file has correct format for normal mode."""
        from app.src.skills.video_compose import run_video_compose

        mock_artifact_store = MagicMock()
        fake_ref = MagicMock()
        fake_ref.storage_ref = "/fake/output.mp4"
        mock_artifact_store.write_file.return_value = fake_ref

        captured_concat_content: str | None = None

        with patch("app.src.skills.video_compose.check_ffmpeg_available", return_value=(True, "ffmpeg version 6")), \
             patch("app.src.skills.video_compose.run_ffmpeg") as mock_ffmpeg:

            def _fake_ffmpeg(args: list[str]) -> MagicMock:
                nonlocal captured_concat_content
                # Find the concat file path: it follows "-i" after "-f concat"
                if "concat" in args:
                    concat_idx = args.index("-i")
                    concat_file = args[concat_idx + 1]
                    if os.path.exists(concat_file):
                        captured_concat_content = Path(concat_file).read_text(encoding="utf-8")

                output_path = args[-1]
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(b"\x00\x00\x00 ftypisom")
                return MagicMock(returncode=0)

            mock_ffmpeg.side_effect = _fake_ffmpeg

            matched_segments = _make_matched_segments(fallback_mode=False, num_matches=2)
            clip_manifest = _make_clip_manifest(num_clips=2)
            voiceover_timing = _make_voiceover_timing()
            subtitle_ref = _make_subtitlesrt(tmp_path)

            run_video_compose(
                matched_segments=matched_segments,
                voiceover_timing=voiceover_timing,
                subtitle_ref=subtitle_ref,
                clip_manifest=clip_manifest,
                artifact_store=mock_artifact_store,
                task_id="test-concat",
            )

        # Verify concat file content
        assert captured_concat_content is not None
        # Should contain file directives for clips
        assert "file" in captured_concat_content
        assert "inpoint" in captured_concat_content
        assert "outpoint" in captured_concat_content
        # Should reference clip paths from clip_manifest
        assert "/fake/clip_0.mp4" in captured_concat_content
        assert "/fake/clip_1.mp4" in captured_concat_content


# ---------------------------------------------------------------------------
# Test 7: StepRunner video_compose dispatch
# ---------------------------------------------------------------------------

class TestStepRunnerVideoCompose:
    def test_step_runner_video_compose(self, tmp_path: Path) -> None:
        """StepRunner dispatches video_compose skill correctly."""
        store, artifacts, runner = _setup_runner(tmp_path)

        task = store.create_task(
            video_type="knowledge_share",
            input_kind="topic",
            input_text="test compose",
            source_links=[],
        )
        store.init_steps(task.id, ["video_compose"])

        # Write matched_segments artifact from material_match step
        matched_segments = _make_matched_segments(fallback_mode=False)
        ms_ref = artifacts.write_json(
            task_id=task.id,
            step_key="material_match",
            artifact_type="matched_segments",
            payload=matched_segments,
        )
        store.add_artifact(
            task_id=task.id,
            step_key="material_match",
            artifact_type=ArtifactType.parsed_json,
            storage_ref=ms_ref.storage_ref,
            metadata={"kind": "matched_segments"},
        )

        # Write voiceover_timing artifact from voiceover step
        voiceover_timing = _make_voiceover_timing()
        vo_ref = artifacts.write_json(
            task_id=task.id,
            step_key="voiceover",
            artifact_type="voiceover_timing",
            payload=voiceover_timing,
        )
        store.add_artifact(
            task_id=task.id,
            step_key="voiceover",
            artifact_type=ArtifactType.parsed_json,
            storage_ref=vo_ref.storage_ref,
            metadata={"kind": "voiceover_timing"},
        )

        # Write subtitle artifact from subtitle step
        srt_path = _make_subtitlesrt(tmp_path / "srt_dir")
        store.add_artifact(
            task_id=task.id,
            step_key="subtitle",
            artifact_type=ArtifactType.subtitle,
            storage_ref=srt_path,
            metadata={"kind": "subtitle"},
        )

        # Write clip_manifest artifact from material_extract step
        clip_manifest = _make_clip_manifest()
        cm_ref = artifacts.write_json(
            task_id=task.id,
            step_key="material_extract",
            artifact_type="clip_manifest",
            payload=clip_manifest,
        )
        store.add_artifact(
            task_id=task.id,
            step_key="material_extract",
            artifact_type=ArtifactType.parsed_json,
            storage_ref=cm_ref.storage_ref,
            metadata={"kind": "clip_manifest"},
        )

        # Mock the video_compose skill
        fake_compose_result = {
            "duration_seconds": 30.5,
            "resolution": "1280x720",
            "has_visual": True,
            "has_audio": True,
            "has_subtitles": True,
            "fallback_mode": False,
            "storage_ref": "/fake/output.mp4",
        }
        mock_skill = MagicMock(return_value=fake_compose_result)

        with patch.dict("app.src.workers.step_runner.STEP_SKILLS", {"video_compose": mock_skill}):
            executed = runner.run_step(task_id=task.id, step_key="video_compose")

        assert executed is True

        step = store.get_step(task.id, "video_compose")
        assert step is not None
        assert step.status == StepStatus.completed

        mock_skill.assert_called_once()
        call_kwargs = mock_skill.call_args[1]
        assert call_kwargs["task_id"] == task.id

        # Verify final_video artifact was registered
        arts = store.list_artifacts(task.id)
        video_arts = [a for a in arts if a.artifact_type == ArtifactType.final_video]
        assert len(video_arts) >= 1

        # Verify parsed_json (compose_log) artifact was registered
        parsed_arts = [
            a for a in arts
            if a.step_key == "video_compose" and a.artifact_type == ArtifactType.parsed_json
        ]
        assert len(parsed_arts) >= 1


# ---------------------------------------------------------------------------
# Test 8: StepRunner video_compose skill registered
# ---------------------------------------------------------------------------

class TestStepRunnerVideoComposeSkillRegistered:
    def test_step_runner_video_compose_skill_registered(self) -> None:
        """Verify 'video_compose' is registered in STEP_SKILLS."""
        assert "video_compose" in STEP_SKILLS

        from app.src.skills.video_compose import run_video_compose
        assert STEP_SKILLS["video_compose"] is run_video_compose
