"""Feature 004 T005: Subtitle skill + StepRunner integration tests."""
from __future__ import annotations

import json
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

def _make_voiceover_timing(
    *,
    num_segments: int = 3,
    include_word_boundaries: bool = True,
    long_segment_index: int | None = None,
) -> dict[str, Any]:
    """Build a voiceover_timing dict matching T002 output schema."""
    segments: list[dict[str, Any]] = []

    texts = [
        "First segment text",
        "Second segment text",
        "Third segment text",
        "Fourth segment text",
        "Fifth segment text",
    ]

    base_duration = 5.0

    for i in range(num_segments):
        duration = base_duration
        if long_segment_index is not None and i == long_segment_index:
            duration = 12.5

        word_boundaries: list[dict[str, Any]] = []
        if include_word_boundaries:
            words = texts[i % len(texts)].split()
            offset = 0
            for w in words:
                word_boundaries.append({
                    "text": w,
                    "offset_ms": offset,
                    "duration_ms": 300,
                })
                offset += 300

        segments.append({
            "segment_index": i,
            "voiceover_text": texts[i % len(texts)],
            "duration_seconds": duration,
            "word_boundaries": word_boundaries,
        })

    total = sum(s["duration_seconds"] for s in segments)
    return {
        "segments": segments,
        "total_duration_seconds": total,
    }


def _make_timing_with_specific_durations(
    durations: list[float],
) -> dict[str, Any]:
    """Build timing data with specific segment durations."""
    texts = [
        "Alpha segment",
        "Beta segment",
        "Gamma segment",
        "Delta segment",
        "Epsilon segment",
    ]
    segments: list[dict[str, Any]] = []
    for i, dur in enumerate(durations):
        words = texts[i % len(texts)].split()
        wb: list[dict[str, Any]] = []
        offset = 0
        for w in words:
            wb.append({"text": w, "offset_ms": offset, "duration_ms": 300})
            offset += 300
        segments.append({
            "segment_index": i,
            "voiceover_text": texts[i % len(texts)],
            "duration_seconds": dur,
            "word_boundaries": wb,
        })
    return {
        "segments": segments,
        "total_duration_seconds": sum(durations),
    }


def _setup_runner(tmp_path: Path) -> tuple[SqliteStore, ArtifactStore, StepRunner]:
    store = SqliteStore(":memory:")
    artifacts = ArtifactStore(str(tmp_path / "artifacts"))
    mock_adapter = MagicMock()
    runner = StepRunner(store=store, artifact_store=artifacts, llm_adapter=mock_adapter)
    return store, artifacts, runner


# ---------------------------------------------------------------------------
# Test 1: Basic 3 segments with word_boundaries
# ---------------------------------------------------------------------------

class TestSubtitleBasic:
    def test_subtitle_basic(self, tmp_path: Path) -> None:
        """3 segments with word_boundaries produce correct SRT entries and entry count."""
        from app.src.skills.subtitle import run_subtitle

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        timing = _make_voiceover_timing(num_segments=3)

        result = run_subtitle(
            voiceover_timing=timing,
            artifact_store=artifact_store,
            task_id="test-basic",
        )

        assert result["entry_count"] == 3
        assert result["total_duration_seconds"] == 15.0
        assert result["source"] == "edge_tts_timing"
        assert "srt_ref" in result

        # Read the SRT file and verify content
        srt_path = result["srt_ref"]
        srt_content = Path(srt_path).read_text(encoding="utf-8")
        entries = [e.strip() for e in srt_content.strip().split("\n\n") if e.strip()]
        assert len(entries) == 3

        # First entry should start at 00:00:00,000
        assert "00:00:00,000" in entries[0]


# ---------------------------------------------------------------------------
# Test 2: Empty timing
# ---------------------------------------------------------------------------

class TestSubtitleEmptyTiming:
    def test_subtitle_empty_timing(self, tmp_path: Path) -> None:
        """Empty segments produce empty SRT content."""
        from app.src.skills.subtitle import run_subtitle

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        timing: dict[str, Any] = {
            "segments": [],
            "total_duration_seconds": 0.0,
        }

        result = run_subtitle(
            voiceover_timing=timing,
            artifact_store=artifact_store,
            task_id="test-empty",
        )

        assert result["entry_count"] == 0
        assert result["total_duration_seconds"] == 0.0

        srt_content = Path(result["srt_ref"]).read_text(encoding="utf-8").strip()
        assert srt_content == ""


# ---------------------------------------------------------------------------
# Test 3: No word_boundaries — fallback to segment-level timing
# ---------------------------------------------------------------------------

class TestSubtitleNoWordBoundaries:
    def test_subtitle_no_word_boundaries(self, tmp_path: Path) -> None:
        """Segments without word_boundaries use duration_seconds for timing."""
        from app.src.skills.subtitle import run_subtitle

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        timing = _make_voiceover_timing(num_segments=2, include_word_boundaries=False)

        result = run_subtitle(
            voiceover_timing=timing,
            artifact_store=artifact_store,
            task_id="test-no-wb",
        )

        assert result["entry_count"] == 2

        srt_content = Path(result["srt_ref"]).read_text(encoding="utf-8")
        entries = [e.strip() for e in srt_content.strip().split("\n\n") if e.strip()]
        assert len(entries) == 2

        # First entry should span the first segment's full duration
        # duration_seconds=5.0 -> 5000ms -> 00:00:05,000
        lines = entries[0].split("\n")
        timestamp_line = lines[1]
        assert "00:00:00,000 --> 00:00:05,000" == timestamp_line


# ---------------------------------------------------------------------------
# Test 4: Long segment split
# ---------------------------------------------------------------------------

class TestSubtitleLongSegmentSplit:
    def test_subtitle_long_segment_split(self, tmp_path: Path) -> None:
        """A segment > 10s is split into 2 SRT entries."""
        from app.src.skills.subtitle import run_subtitle

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))

        # Build a long segment with many words
        words = ["word"] * 30
        word_boundaries = [
            {"text": f"w{i}", "offset_ms": i * 400, "duration_ms": 400}
            for i in range(30)
        ]

        timing: dict[str, Any] = {
            "segments": [
                {
                    "segment_index": 0,
                    "voiceover_text": "This is a very long segment that exceeds ten seconds",
                    "duration_seconds": 12.5,
                    "word_boundaries": word_boundaries,
                },
            ],
            "total_duration_seconds": 12.5,
        }

        result = run_subtitle(
            voiceover_timing=timing,
            artifact_store=artifact_store,
            task_id="test-split",
        )

        # One long segment should be split into 2 entries
        assert result["entry_count"] == 2

        srt_content = Path(result["srt_ref"]).read_text(encoding="utf-8")
        entries = [e.strip() for e in srt_content.strip().split("\n\n") if e.strip()]
        assert len(entries) == 2

        # Second entry should have a start time after the first entry's end
        first_lines = entries[0].split("\n")
        second_lines = entries[1].split("\n")

        # Extract end time of first entry
        first_ts = first_lines[1]  # "HH:MM:SS,mmm --> HH:MM:SS,mmm"
        first_end = first_ts.split(" --> ")[1]

        # Extract start time of second entry
        second_ts = second_lines[1]
        second_start = second_ts.split(" --> ")[0]

        assert first_end == second_start


# ---------------------------------------------------------------------------
# Test 5: SRT timestamp format
# ---------------------------------------------------------------------------

class TestSubtitleSrtFormat:
    def test_subtitle_srt_format(self, tmp_path: Path) -> None:
        """Verify exact SRT timestamp format HH:MM:SS,mmm."""
        from app.src.skills.subtitle import ms_to_srt

        # Test known conversions
        assert ms_to_srt(0) == "00:00:00,000"
        assert ms_to_srt(1000) == "00:00:01,000"
        assert ms_to_srt(60000) == "00:01:00,000"
        assert ms_to_srt(3600000) == "01:00:00,000"
        assert ms_to_srt(5230) == "00:00:05,230"
        assert ms_to_srt(3661500) == "01:01:01,500"
        assert ms_to_srt(7384500) == "02:03:04,500"


# ---------------------------------------------------------------------------
# Test 6: SRT file written to artifact store
# ---------------------------------------------------------------------------

class TestSubtitleFileWritten:
    def test_subtitle_file_written(self, tmp_path: Path) -> None:
        """Verify .srt file is written to artifact store."""
        from app.src.skills.subtitle import run_subtitle

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        timing = _make_voiceover_timing(num_segments=1)

        result = run_subtitle(
            voiceover_timing=timing,
            artifact_store=artifact_store,
            task_id="test-file-written",
        )

        srt_path = Path(result["srt_ref"])
        assert srt_path.exists()
        assert srt_path.suffix == ".srt"

        content = srt_path.read_text(encoding="utf-8")
        assert "-->" in content
        assert "00:00:00,000" in content


# ---------------------------------------------------------------------------
# Test 7: StepRunner subtitle dispatch
# ---------------------------------------------------------------------------

class TestStepRunnerSubtitle:
    def test_step_runner_subtitle(self, tmp_path: Path) -> None:
        """StepRunner dispatches subtitle skill correctly."""
        store, artifacts, runner = _setup_runner(tmp_path)

        task = store.create_task(
            video_type="knowledge_share",
            input_kind="topic",
            input_text="test subtitle",
            source_links=[],
        )
        store.init_steps(task.id, ["subtitle"])

        # Write a voiceover_timing artifact so _run_subtitle can read it
        timing_data = _make_voiceover_timing(num_segments=2)
        timing_ref = artifacts.write_json(
            task_id=task.id,
            step_key="voiceover",
            artifact_type="voiceover_timing",
            payload=timing_data,
        )
        store.add_artifact(
            task_id=task.id,
            step_key="voiceover",
            artifact_type=ArtifactType.parsed_json,
            storage_ref=timing_ref.storage_ref,
            metadata={"kind": "voiceover_timing"},
        )

        # Mock the subtitle skill
        fake_result = {
            "entry_count": 2,
            "total_duration_seconds": 10.0,
            "source": "edge_tts_timing",
            "srt_ref": "/fake/subs.srt",
        }

        mock_skill = MagicMock(return_value=fake_result)
        with patch.dict("app.src.workers.step_runner.STEP_SKILLS", {"subtitle": mock_skill}):
            executed = runner.run_step(task_id=task.id, step_key="subtitle")

        assert executed is True

        step = store.get_step(task.id, "subtitle")
        assert step is not None
        assert step.status == StepStatus.completed

        mock_skill.assert_called_once()
        call_kwargs = mock_skill.call_args[1]
        assert call_kwargs["task_id"] == task.id


# ---------------------------------------------------------------------------
# Test 8: StepRunner subtitle skill registered
# ---------------------------------------------------------------------------

class TestStepRunnerSubtitleSkillRegistered:
    def test_step_runner_subtitle_skill_registered(self) -> None:
        """Verify 'subtitle' is registered in STEP_SKILLS."""
        assert "subtitle" in STEP_SKILLS

        from app.src.skills.subtitle import run_subtitle
        assert STEP_SKILLS["subtitle"] is run_subtitle


# ---------------------------------------------------------------------------
# Test 9: Global offset tracking across segments
# ---------------------------------------------------------------------------

class TestSubtitleGlobalOffset:
    def test_subtitle_global_offset_accumulates(self, tmp_path: Path) -> None:
        """Timestamps accumulate global offset from previous segments."""
        from app.src.skills.subtitle import run_subtitle

        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))

        # Segment 0: 3.0s, segment 1: 2.0s, segment 2: 1.5s
        timing = _make_timing_with_specific_durations([3.0, 2.0, 1.5])

        result = run_subtitle(
            voiceover_timing=timing,
            artifact_store=artifact_store,
            task_id="test-offset",
        )

        srt_content = Path(result["srt_ref"]).read_text(encoding="utf-8")
        entries = [e.strip() for e in srt_content.strip().split("\n\n") if e.strip()]
        assert len(entries) == 3

        # Second entry should start at ~3000ms (end of first segment)
        second_ts = entries[1].split("\n")[1]
        second_start = second_ts.split(" --> ")[0]
        assert second_start == "00:00:03,000"

        # Third entry should start at ~5000ms (3.0 + 2.0)
        third_ts = entries[2].split("\n")[1]
        third_start = third_ts.split(" --> ")[0]
        assert third_start == "00:00:05,000"
