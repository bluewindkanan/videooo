"""Feature 004 T002: Voiceover skill + StepRunner integration tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import ArtifactType, StepStatus
from app.src.storage.sqlite import SqliteStore
from app.src.workers.step_runner import STEP_SKILLS, StepRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_storyboard_segments() -> list[dict[str, Any]]:
    return [
        {
            "segment_index": 0,
            "voiceover_text": "Hello world",
            "visual_intent": "show title",
            "expected_keywords": ["hello"],
            "estimated_start_seconds": 0.0,
            "estimated_end_seconds": 3.0,
        },
        {
            "segment_index": 1,
            "voiceover_text": "This is a test",
            "visual_intent": "show content",
            "expected_keywords": ["test"],
            "estimated_start_seconds": 3.0,
            "estimated_end_seconds": 6.0,
        },
    ]


def _make_fake_tts_chunks(text: str, base_offset: int = 0) -> list[dict[str, Any]]:
    """Create fake edge-tts TTSChunk stream output for a given text."""
    words = text.split()
    chunks: list[dict[str, Any]] = []
    offset = base_offset
    for word in words:
        chunks.append({
            "type": "WordBoundary",
            "offset": offset,
            "duration": 200,
            "text": word,
        })
        offset += 200
    # Add audio chunks (fake mp3 bytes)
    chunks.append({"type": "audio", "data": b"\xff\xfb\x90\x00" * 100})
    return chunks


def _setup_runner(tmp_path: Path) -> tuple[SqliteStore, ArtifactStore, StepRunner]:
    store = SqliteStore(":memory:")
    artifacts = ArtifactStore(str(tmp_path / "artifacts"))
    mock_adapter = MagicMock()
    runner = StepRunner(store=store, artifact_store=artifacts, llm_adapter=mock_adapter)
    return store, artifacts, runner


# ---------------------------------------------------------------------------
# Test: run_voiceover basic
# ---------------------------------------------------------------------------

class TestRunVoiceoverBasic:
    """Test basic voiceover generation with 2 segments."""

    @patch("app.src.skills.voiceover.probe_duration", return_value=5.23)
    @patch("app.src.skills.voiceover.run_ffmpeg")
    def test_run_voiceover_basic(self, mock_ffmpeg: MagicMock, mock_probe: MagicMock, tmp_path: Path) -> None:
        from app.src.skills.voiceover import run_voiceover

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        segments = _make_storyboard_segments()

        # Build fake chunk streams per segment
        seg0_chunks = _make_fake_tts_chunks("Hello world", base_offset=0)
        seg1_chunks = _make_fake_tts_chunks("This is a test", base_offset=0)

        mock_communicate_instances = []

        def _make_communicate(text: str, voice: str) -> MagicMock:
            inst = MagicMock()
            if text == "Hello world":
                inst.stream_sync.return_value = iter(seg0_chunks)
            else:
                inst.stream_sync.return_value = iter(seg1_chunks)
            mock_communicate_instances.append(inst)
            return inst

        with patch("app.src.skills.voiceover.edge_tts") as mock_edge_tts:
            mock_edge_tts.Communicate.side_effect = _make_communicate

            result = run_voiceover(
                storyboard_segments=segments,
                artifact_store=artifact_store,
                task_id="test-task-001",
            )

        # Verify timing_data structure
        assert "segments" in result
        assert "total_duration_seconds" in result
        assert "full_audio_ref" in result
        assert len(result["segments"]) == 2

        seg0 = result["segments"][0]
        assert seg0["segment_index"] == 0
        assert seg0["voiceover_text"] == "Hello world"
        assert "segment_audio_ref" in seg0
        assert "duration_seconds" in seg0
        assert "word_boundaries" in seg0
        assert len(seg0["word_boundaries"]) == 2  # "Hello" and "world"

        # Verify word_boundaries structure
        wb0 = seg0["word_boundaries"][0]
        assert "text" in wb0
        assert "offset_ms" in wb0
        assert "duration_ms" in wb0


# ---------------------------------------------------------------------------
# Test: empty segments raises VoiceoverError
# ---------------------------------------------------------------------------

class TestRunVoiceoverEmptySegments:
    def test_run_voiceover_empty_segments(self) -> None:
        from app.src.skills.voiceover import VoiceoverError, run_voiceover

        artifact_store = MagicMock()
        with pytest.raises(VoiceoverError):
            run_voiceover(
                storyboard_segments=[],
                artifact_store=artifact_store,
                task_id="test-task",
            )


# ---------------------------------------------------------------------------
# Test: FFmpeg concat called
# ---------------------------------------------------------------------------

class TestRunVoiceoverConcatFFmpeg:
    @patch("app.src.skills.voiceover.probe_duration", return_value=3.0)
    @patch("app.src.skills.voiceover.run_ffmpeg")
    def test_run_voiceover_concat_calls_ffmpeg(self, mock_ffmpeg: MagicMock, mock_probe: MagicMock, tmp_path: Path) -> None:
        from app.src.skills.voiceover import run_voiceover

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        segments = _make_storyboard_segments()

        seg0_chunks = _make_fake_tts_chunks("Hello world")
        seg1_chunks = _make_fake_tts_chunks("This is a test")

        def _make_communicate(text: str, voice: str) -> MagicMock:
            inst = MagicMock()
            if text == "Hello world":
                inst.stream_sync.return_value = iter(seg0_chunks)
            else:
                inst.stream_sync.return_value = iter(seg1_chunks)
            return inst

        with patch("app.src.skills.voiceover.edge_tts") as mock_edge_tts:
            mock_edge_tts.Communicate.side_effect = _make_communicate

            run_voiceover(
                storyboard_segments=segments,
                artifact_store=artifact_store,
                task_id="test-task-002",
            )

        # FFmpeg should have been called for concat
        mock_ffmpeg.assert_called_once()
        call_args = mock_ffmpeg.call_args[0][0]
        assert "-f" in call_args
        assert "concat" in call_args


# ---------------------------------------------------------------------------
# Test: word boundaries captured
# ---------------------------------------------------------------------------

class TestRunVoiceoverWordBoundaries:
    @patch("app.src.skills.voiceover.probe_duration", return_value=2.5)
    @patch("app.src.skills.voiceover.run_ffmpeg")
    def test_run_voiceover_word_boundaries(self, mock_ffmpeg: MagicMock, mock_probe: MagicMock, tmp_path: Path) -> None:
        from app.src.skills.voiceover import run_voiceover

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        segments = _make_storyboard_segments()

        seg0_chunks = [
            {"type": "WordBoundary", "offset": 0, "duration": 150, "text": "Hello"},
            {"type": "WordBoundary", "offset": 150, "duration": 200, "text": "world"},
            {"type": "audio", "data": b"\xff\xfb\x90\x00" * 50},
        ]
        seg1_chunks = [
            {"type": "WordBoundary", "offset": 0, "duration": 100, "text": "This"},
            {"type": "WordBoundary", "offset": 100, "duration": 100, "text": "is"},
            {"type": "WordBoundary", "offset": 200, "duration": 100, "text": "a"},
            {"type": "WordBoundary", "offset": 300, "duration": 200, "text": "test"},
            {"type": "audio", "data": b"\xff\xfb\x90\x00" * 50},
        ]

        def _make_communicate(text: str, voice: str) -> MagicMock:
            inst = MagicMock()
            if text == "Hello world":
                inst.stream_sync.return_value = iter(seg0_chunks)
            else:
                inst.stream_sync.return_value = iter(seg1_chunks)
            return inst

        with patch("app.src.skills.voiceover.edge_tts") as mock_edge_tts:
            mock_edge_tts.Communicate.side_effect = _make_communicate

            result = run_voiceover(
                storyboard_segments=segments,
                artifact_store=artifact_store,
                task_id="test-task-003",
            )

        # Verify word boundaries
        seg0_wb = result["segments"][0]["word_boundaries"]
        assert len(seg0_wb) == 2
        assert seg0_wb[0]["text"] == "Hello"
        assert seg0_wb[0]["offset_ms"] == 0
        assert seg0_wb[0]["duration_ms"] == 150
        assert seg0_wb[1]["text"] == "world"
        assert seg0_wb[1]["offset_ms"] == 150
        assert seg0_wb[1]["duration_ms"] == 200

        seg1_wb = result["segments"][1]["word_boundaries"]
        assert len(seg1_wb) == 4
        assert seg1_wb[0]["text"] == "This"


# ---------------------------------------------------------------------------
# Test: StepRunner voiceover dispatch
# ---------------------------------------------------------------------------

class TestStepRunnerVoiceover:
    def test_step_runner_voiceover(self, tmp_path: Path) -> None:
        store, artifacts, runner = _setup_runner(tmp_path)

        # Create task and steps
        task = store.create_task(
            video_type="knowledge_share",
            input_kind="topic",
            input_text="test voiceover",
            source_links=[],
        )
        store.init_steps(task.id, ["voiceover"])

        # Write a storyboard artifact so _run_voiceover can read it
        storyboard_ref = artifacts.write_json(
            task_id=task.id,
            step_key="storyboard",
            artifact_type="storyboard_segments",
            payload=_make_storyboard_segments(),
        )
        store.add_artifact(
            task_id=task.id,
            step_key="storyboard",
            artifact_type=ArtifactType.parsed_json,
            storage_ref=storyboard_ref.storage_ref,
            metadata={"kind": "storyboard_segments"},
        )

        # Mock the voiceover skill via STEP_SKILLS (same path _run_skill uses)
        fake_timing_data = {
            "segments": [
                {
                    "segment_index": 0,
                    "voiceover_text": "Hello world",
                    "segment_audio_ref": "/fake/seg_0.mp3",
                    "duration_seconds": 2.5,
                    "word_boundaries": [{"text": "Hello", "offset_ms": 0, "duration_ms": 150}],
                },
            ],
            "total_duration_seconds": 2.5,
            "full_audio_ref": "/fake/full.mp3",
        }

        mock_skill = MagicMock(return_value=fake_timing_data)
        with patch.dict("app.src.workers.step_runner.STEP_SKILLS", {"voiceover": mock_skill}):
            executed = runner.run_step(task_id=task.id, step_key="voiceover")

        assert executed is True

        step = store.get_step(task.id, "voiceover")
        assert step is not None
        assert step.status == StepStatus.completed

        # Verify skill was called
        mock_skill.assert_called_once()
        call_kwargs = mock_skill.call_args[1]
        assert call_kwargs["task_id"] == task.id

    def test_step_runner_voiceover_skill_registered(self) -> None:
        """Verify 'voiceover' is registered in STEP_SKILLS."""
        assert "voiceover" in STEP_SKILLS

        from app.src.skills.voiceover import run_voiceover
        assert STEP_SKILLS["voiceover"] is run_voiceover


# ---------------------------------------------------------------------------
# Test: VoiceoverError exception exists
# ---------------------------------------------------------------------------

class TestVoiceoverError:
    def test_voiceover_error_is_exception(self) -> None:
        from app.src.skills.voiceover import VoiceoverError

        assert issubclass(VoiceoverError, Exception)
        err = VoiceoverError("test error")
        assert str(err) == "test error"


# ---------------------------------------------------------------------------
# Test: voice configurable via env var
# ---------------------------------------------------------------------------

class TestVoiceConfig:
    @patch("app.src.skills.voiceover.probe_duration", return_value=1.0)
    @patch("app.src.skills.voiceover.run_ffmpeg")
    def test_default_voice_is_xiaoxiao(self, mock_ffmpeg: MagicMock, mock_probe: MagicMock, tmp_path: Path) -> None:
        from app.src.skills.voiceover import run_voiceover

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        segments = [{"segment_index": 0, "voiceover_text": "hi"}]

        chunks = [
            {"type": "WordBoundary", "offset": 0, "duration": 100, "text": "hi"},
            {"type": "audio", "data": b"\xff\xfb\x90\x00" * 50},
        ]

        with patch("app.src.skills.voiceover.edge_tts") as mock_edge_tts:
            mock_inst = MagicMock()
            mock_inst.stream_sync.return_value = iter(chunks)
            mock_edge_tts.Communicate.return_value = mock_inst

            run_voiceover(
                storyboard_segments=segments,  # type: ignore[arg-type]
                artifact_store=artifact_store,
                task_id="test-voice",
            )

        mock_edge_tts.Communicate.assert_called_once()
        call_args = mock_edge_tts.Communicate.call_args
        assert call_args[0][1] == "zh-CN-XiaoxiaoNeural"
