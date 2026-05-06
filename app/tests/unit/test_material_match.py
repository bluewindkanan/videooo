"""Unit tests for material_match skill + StepRunner integration."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import ArtifactType, StepStatus
from app.src.storage.sqlite import SqliteStore


# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------

def _voiceover_timing(segments: list[dict]) -> dict:
    """Build a voiceover_timing dict matching the voiceover skill output schema."""
    return {
        "segments": segments,
        "total_duration_seconds": sum(s["duration_seconds"] for s in segments),
    }


def _segment(index: int, duration: float, text: str = "text") -> dict:
    return {
        "segment_index": index,
        "voiceover_text": text,
        "duration_seconds": duration,
    }


def _clip(index: int, duration: float, start: float | None = None) -> dict:
    s = start if start is not None else index * duration
    return {
        "clip_index": index,
        "source_ref": f"/fake/source_{index}.mp4",
        "start_seconds": s,
        "end_seconds": s + duration,
        "duration_seconds": duration,
        "storage_ref": f"/fake/clip_{index}.mp4",
    }


def _clip_manifest(clips: list[dict]) -> dict:
    return {
        "clips": clips,
        "total_clip_duration_seconds": sum(c["duration_seconds"] for c in clips),
    }


# ---------------------------------------------------------------------------
# 1. test_match_basic
# ---------------------------------------------------------------------------


class TestMatchBasic:
    """3 segments (5.0, 3.0, 4.0) + 5 clips (each 3.0s) -> verify assignments."""

    def test_match_basic(self) -> None:
        from app.src.skills.material_match import run_material_match

        timing = _voiceover_timing([
            _segment(0, 5.0),
            _segment(1, 3.0),
            _segment(2, 4.0),
        ])
        manifest = _clip_manifest([_clip(i, 3.0) for i in range(5)])

        result = run_material_match(voiceover_timing=timing, clip_manifest=manifest)

        assert result["fallback_mode"] is False
        assert len(result["matches"]) == 3

        # Segment 0 (5.0s): clip 0 (3.0s) + clip 1 (2.0s of 3.0s)
        # Clips: [0,3) [3,6) [6,9) [9,12) [12,15)
        seg0 = result["matches"][0]
        assert seg0["segment_index"] == 0
        assert seg0["voiceover_duration"] == 5.0
        assert len(seg0["assigned_clips"]) == 2
        assert seg0["assigned_clips"][0]["clip_index"] == 0
        assert seg0["assigned_clips"][0]["start_seconds"] == 0.0
        assert seg0["assigned_clips"][0]["end_seconds"] == 3.0
        assert seg0["assigned_clips"][0]["duration_used"] == 3.0
        assert seg0["assigned_clips"][1]["clip_index"] == 1
        assert seg0["assigned_clips"][1]["start_seconds"] == 3.0
        assert seg0["assigned_clips"][1]["end_seconds"] == 5.0
        assert seg0["assigned_clips"][1]["duration_used"] == 2.0

        # Segment 1 (3.0s): clip 1 remaining (1.0s from [5,6)) + clip 2 (2.0s from [6,8))
        seg1 = result["matches"][1]
        assert seg1["segment_index"] == 1
        assert seg1["voiceover_duration"] == 3.0
        assert len(seg1["assigned_clips"]) == 2
        assert seg1["assigned_clips"][0]["clip_index"] == 1
        assert seg1["assigned_clips"][0]["start_seconds"] == 5.0
        assert seg1["assigned_clips"][0]["end_seconds"] == 6.0
        assert seg1["assigned_clips"][0]["duration_used"] == 1.0
        assert seg1["assigned_clips"][1]["clip_index"] == 2
        assert seg1["assigned_clips"][1]["start_seconds"] == 6.0
        assert seg1["assigned_clips"][1]["end_seconds"] == 8.0
        assert seg1["assigned_clips"][1]["duration_used"] == 2.0

        # Segment 2 (4.0s): clip 2 remaining (1.0s from [8,9)) + clip 3 (3.0s from [9,12))
        seg2 = result["matches"][2]
        assert seg2["segment_index"] == 2
        assert seg2["voiceover_duration"] == 4.0
        assert len(seg2["assigned_clips"]) == 2
        assert seg2["assigned_clips"][0]["clip_index"] == 2
        assert seg2["assigned_clips"][0]["start_seconds"] == 8.0
        assert seg2["assigned_clips"][0]["end_seconds"] == 9.0
        assert seg2["assigned_clips"][0]["duration_used"] == 1.0
        assert seg2["assigned_clips"][1]["clip_index"] == 3
        assert seg2["assigned_clips"][1]["start_seconds"] == 9.0
        assert seg2["assigned_clips"][1]["end_seconds"] == 12.0
        assert seg2["assigned_clips"][1]["duration_used"] == 3.0


# ---------------------------------------------------------------------------
# 2. test_match_empty_clips_fallback
# ---------------------------------------------------------------------------


class TestMatchEmptyClipsFallback:
    """No clips -> fallback_mode=true, assigned_clips empty."""

    def test_match_empty_clips_fallback(self) -> None:
        from app.src.skills.material_match import run_material_match

        timing = _voiceover_timing([_segment(0, 5.0)])
        manifest = _clip_manifest([])

        result = run_material_match(voiceover_timing=timing, clip_manifest=manifest)

        assert result["fallback_mode"] is True
        assert len(result["matches"]) == 1
        assert result["matches"][0]["assigned_clips"] == []


# ---------------------------------------------------------------------------
# 3. test_match_clip_looping
# ---------------------------------------------------------------------------


class TestMatchClipLooping:
    """Clips exhaust -> loops back to clip 0."""

    def test_match_clip_looping(self) -> None:
        from app.src.skills.material_match import run_material_match

        timing = _voiceover_timing([
            _segment(0, 4.0),  # clip 0 (2.0s) + clip 1 (2.0s) -> exhaust both
            _segment(1, 3.0),  # clip 0 again (2.0s) + clip 1 (1.0s) -> loops
        ])
        manifest = _clip_manifest([_clip(0, 2.0), _clip(1, 2.0)])

        result = run_material_match(voiceover_timing=timing, clip_manifest=manifest)

        assert result["fallback_mode"] is False
        assert len(result["matches"]) == 2

        # Segment 0: clips 0 + 1
        seg0 = result["matches"][0]
        assert len(seg0["assigned_clips"]) == 2
        assert seg0["assigned_clips"][0]["clip_index"] == 0
        assert seg0["assigned_clips"][1]["clip_index"] == 1

        # Segment 1: clips 0 + 1 (looped)
        seg1 = result["matches"][1]
        assert len(seg1["assigned_clips"]) == 2
        assert seg1["assigned_clips"][0]["clip_index"] == 0
        assert seg1["assigned_clips"][1]["clip_index"] == 1


# ---------------------------------------------------------------------------
# 4. test_match_single_clip
# ---------------------------------------------------------------------------


class TestMatchSingleClip:
    """1 clip (30s) for 5 segments -> all use portions of same clip."""

    def test_match_single_clip(self) -> None:
        from app.src.skills.material_match import run_material_match

        seg_durations = [3.0, 5.0, 4.0, 6.0, 2.0]
        timing = _voiceover_timing([
            _segment(i, d) for i, d in enumerate(seg_durations)
        ])
        manifest = _clip_manifest([_clip(0, 30.0, start=0.0)])

        result = run_material_match(voiceover_timing=timing, clip_manifest=manifest)

        assert result["fallback_mode"] is False
        assert len(result["matches"]) == 5

        # Every assigned clip should be clip 0
        for match in result["matches"]:
            for ac in match["assigned_clips"]:
                assert ac["clip_index"] == 0

        # Verify sequential start positions
        # Seg 0: [0.0, 3.0)
        assert result["matches"][0]["assigned_clips"][0]["start_seconds"] == 0.0
        assert result["matches"][0]["assigned_clips"][0]["end_seconds"] == 3.0
        # Seg 1: [3.0, 8.0)
        assert result["matches"][1]["assigned_clips"][0]["start_seconds"] == 3.0
        assert result["matches"][1]["assigned_clips"][0]["end_seconds"] == 8.0
        # Seg 2: [8.0, 12.0)
        assert result["matches"][2]["assigned_clips"][0]["start_seconds"] == 8.0
        assert result["matches"][2]["assigned_clips"][0]["end_seconds"] == 12.0


# ---------------------------------------------------------------------------
# 5. test_match_exact_duration
# ---------------------------------------------------------------------------


class TestMatchExactDuration:
    """Clips total = segments total -> no looping needed."""

    def test_match_exact_duration(self) -> None:
        from app.src.skills.material_match import run_material_match

        timing = _voiceover_timing([
            _segment(0, 4.0),
            _segment(1, 6.0),
        ])
        # 2 clips totaling 10.0s (same as segment total)
        manifest = _clip_manifest([_clip(0, 4.0), _clip(1, 6.0)])

        result = run_material_match(voiceover_timing=timing, clip_manifest=manifest)

        assert result["fallback_mode"] is False
        assert len(result["matches"]) == 2

        seg0 = result["matches"][0]
        assert len(seg0["assigned_clips"]) == 1
        assert seg0["assigned_clips"][0]["clip_index"] == 0
        assert seg0["assigned_clips"][0]["duration_used"] == 4.0

        seg1 = result["matches"][1]
        assert len(seg1["assigned_clips"]) == 1
        assert seg1["assigned_clips"][0]["clip_index"] == 1
        assert seg1["assigned_clips"][0]["duration_used"] == 6.0


# ---------------------------------------------------------------------------
# 6. test_step_runner_material_match
# ---------------------------------------------------------------------------


class TestStepRunnerMaterialMatch:
    """Test StepRunner dispatch for material_match."""

    def test_step_runner_material_match(self, tmp_path: Path) -> None:
        from app.src.workers.step_runner import StepRunner

        store = SqliteStore(":memory:")
        artifact_store = ArtifactStore(str(tmp_path / "artifacts"))
        runner = StepRunner(store=store, artifact_store=artifact_store)

        task = store.create_task(
            video_type="knowledge_share",
            input_kind="topic",
            input_text="test material match",
            source_links=[],
        )
        store.init_steps(task.id, ["voiceover", "material_extract", "material_match"])

        # Write voiceover_timing artifact (from voiceover step)
        timing_data = _voiceover_timing([_segment(0, 5.0), _segment(1, 3.0)])
        timing_ref = artifact_store.write_json(
            task_id=task.id,
            step_key="voiceover",
            artifact_type="parsed_json",
            payload=timing_data,
        )
        store.add_artifact(
            task_id=task.id,
            step_key="voiceover",
            artifact_type=ArtifactType.parsed_json,
            storage_ref=timing_ref.storage_ref,
            metadata={"kind": "voiceover_timing"},
        )

        # Write clip_manifest artifact (from material_extract step)
        manifest_data = _clip_manifest([_clip(0, 3.0), _clip(1, 3.0), _clip(2, 3.0)])
        manifest_ref = artifact_store.write_json(
            task_id=task.id,
            step_key="material_extract",
            artifact_type="parsed_json",
            payload=manifest_data,
        )
        store.add_artifact(
            task_id=task.id,
            step_key="material_extract",
            artifact_type=ArtifactType.parsed_json,
            storage_ref=manifest_ref.storage_ref,
            metadata={"kind": "clip_manifest"},
        )

        # Run material_match step
        executed = runner.run_step(task_id=task.id, step_key="material_match")
        assert executed is True

        step = store.get_step(task.id, "material_match")
        assert step is not None
        assert step.status == StepStatus.completed

        # Verify matched_segments artifact was written
        artifacts = store.list_artifacts(task.id)
        matched_artifacts = [
            a for a in artifacts
            if a.step_key == "material_match" and a.artifact_type == ArtifactType.parsed_json
        ]
        assert len(matched_artifacts) == 1
        assert matched_artifacts[0].metadata.get("kind") == "matched_segments"

        # Verify artifact content
        import pathlib
        content = pathlib.Path(matched_artifacts[0].storage_ref).read_text(encoding="utf-8")
        matched_data = json.loads(content)
        assert "matches" in matched_data
        assert matched_data["fallback_mode"] is False


# ---------------------------------------------------------------------------
# 7. test_step_runner_material_match_skill_registered
# ---------------------------------------------------------------------------


class TestStepRunnerMaterialMatchSkillRegistered:
    """Verify 'material_match' is registered in STEP_SKILLS."""

    def test_skill_registered(self) -> None:
        from app.src.workers.step_runner import STEP_SKILLS

        assert "material_match" in STEP_SKILLS


# ---------------------------------------------------------------------------
# 8. test_match_no_voiceover_timing
# ---------------------------------------------------------------------------


class TestMatchNoVoiceoverTiming:
    """Empty timing -> returns empty matches."""

    def test_match_no_voiceover_timing(self) -> None:
        from app.src.skills.material_match import run_material_match

        timing = _voiceover_timing([])
        manifest = _clip_manifest([_clip(0, 5.0)])

        result = run_material_match(voiceover_timing=timing, clip_manifest=manifest)

        assert result["matches"] == []
        assert result["fallback_mode"] is False
