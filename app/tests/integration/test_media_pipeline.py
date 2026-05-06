"""E2E integration tests for the full media pipeline (Feature 004).

Tests exercise the complete 9-step pipeline through the API:
  material_fetch -> script_generation -> storyboard -> review_script ->
  voiceover -> material_extract -> material_match -> subtitle -> video_compose

Tests that require FFmpeg are marked with @requires_ffmpeg and skipped
automatically when FFmpeg is not available.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import struct
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.src.domain.models import ArtifactType, StepStatus
from app.src.server.main import create_app


# ---------------------------------------------------------------------------
# FFmpeg availability guards
# ---------------------------------------------------------------------------

def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _ffmpeg_has_subtitles_filter() -> bool:
    """Check if FFmpeg was compiled with libass (subtitles filter)."""
    if not _ffmpeg_available():
        return False
    result = subprocess.run(
        ["ffmpeg", "-filters"], capture_output=True, text=True, timeout=10
    )
    return "subtitles" in result.stdout


requires_ffmpeg = pytest.mark.skipif(
    not _ffmpeg_available(),
    reason="FFmpeg not available",
)

requires_ffmpeg_subtitles = pytest.mark.skipif(
    not _ffmpeg_has_subtitles_filter(),
    reason="FFmpeg not compiled with libass (subtitles filter unavailable)",
)


# ---------------------------------------------------------------------------
# Test fixture paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
TEST_VIDEO_PATH = FIXTURES_DIR / "test_video.mp4"


# ---------------------------------------------------------------------------
# Canned LLM responses
# ---------------------------------------------------------------------------

def _script_response() -> str:
    return json.dumps({
        "hook": "Did you know that sleep boosts memory?",
        "body": "Recent studies show that 7-9 hours of sleep consolidates learning.",
        "call_to_action": "Follow for more brain hacks!",
        "estimated_duration_seconds": 30,
    })


def _storyboard_response() -> dict:
    return {
        "segments": [
            {
                "segment_index": 0,
                "title": "Hook",
                "voiceover_text": "Did you know that sleep boosts memory?",
                "visual_description": "Close-up of a person sleeping peacefully",
                "duration_seconds": 5,
            },
            {
                "segment_index": 1,
                "title": "Body",
                "voiceover_text": "Recent studies show that 7-9 hours of sleep consolidates learning.",
                "visual_description": "Infographic showing sleep stages",
                "duration_seconds": 8,
            },
        ],
    }


def _review_response() -> dict:
    return {
        "findings": [
            {
                "severity": "info",
                "category": "duration",
                "message": "Estimated duration is within the recommended range.",
            },
        ],
        "overall_score": 8,
        "suggestion": "Consider adding a stronger emotional hook.",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_llm_adapter() -> MagicMock:
    """Mock LLMAdapter whose .chat() returns valid script JSON."""
    adapter = MagicMock()
    adapter.chat.return_value = _script_response()
    return adapter


@pytest.fixture()
def client(tmp_path: Path, mock_llm_adapter: MagicMock) -> TestClient:
    """TestClient wired to in-memory SQLite with mocked LLM."""
    artifact_dir = str(tmp_path / "artifacts")
    with patch("app.src.workers.step_runner.LLMAdapter.from_env", return_value=mock_llm_adapter):
        app = create_app(db_path=":memory:")
        from app.src.artifacts.store import ArtifactStore
        app.state.artifact_store = ArtifactStore(artifact_dir)
        with TestClient(app) as c:
            yield c


def _create_task(
    client: TestClient,
    *,
    topic: str = "How sleep improves memory",
    input_kind: str = "topic",
    source_links: list[str] | None = None,
) -> dict:
    """Helper to POST /api/video-tasks and return the JSON body."""
    body: dict[str, Any] = {
        "input_kind": input_kind,
        "input_text": topic,
        "source_links": source_links or [],
    }
    resp = client.post("/api/video-tasks", json=body)
    assert resp.status_code == 200, f"Create task failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Test 1: Pipeline has 9 steps (no FFmpeg needed)
# ---------------------------------------------------------------------------

class TestPipelineHas9Steps:
    """Verify task creation initializes all 9 pipeline steps."""

    def test_pipeline_has_9_steps(self, client: TestClient) -> None:
        data = _create_task(client, topic="Nine step check")
        task_id = data["task_id"]

        detail = client.get(f"/api/video-tasks/{task_id}")
        assert detail.status_code == 200
        body = detail.json()
        steps = body["steps"]

        from app.src.server.routes.video_tasks import DEFAULT_STEP_KEYS

        # Verify 9 steps exist
        assert len(steps) == 9, f"Expected 9 steps, got {len(steps)}"

        # Verify step_keys match DEFAULT_STEP_KEYS as a set (API returns sorted by step_key ASC)
        step_keys = {s["step_key"] for s in steps}
        assert step_keys == set(DEFAULT_STEP_KEYS), (
            f"Step keys mismatch:\n  got:      {step_keys}\n  expected: {set(DEFAULT_STEP_KEYS)}"
        )

        # Verify all expected step keys are present
        expected_keys = {
            "material_fetch", "script_generation", "storyboard", "review_script",
            "voiceover", "material_extract", "material_match", "subtitle", "video_compose",
        }
        assert step_keys == expected_keys


# ---------------------------------------------------------------------------
# Test 2: No source videos with FAIL injection (no FFmpeg needed)
# ---------------------------------------------------------------------------

class TestNoSourceVideosPipeline:
    """Pipeline stops at material_fetch when input contains FAIL (simulated failure)."""

    def test_no_source_videos_pipeline(self, client: TestClient) -> None:
        data = _create_task(
            client,
            topic="FAIL test topic",
            source_links=["https://example.com/video.mp4"],
        )
        task_id = data["task_id"]

        detail = client.get(f"/api/video-tasks/{task_id}").json()
        steps = {s["step_key"]: s for s in detail["steps"]}

        # material_fetch should have failed (FAIL injection)
        assert steps["material_fetch"]["status"] == "failed", (
            f"material_fetch expected failed, got {steps['material_fetch']['status']}"
        )

        # Pipeline should stop — subsequent steps should NOT be completed
        for step_key in [
            "script_generation", "storyboard", "review_script",
            "voiceover", "material_extract", "material_match",
            "subtitle", "video_compose",
        ]:
            assert steps[step_key]["status"] != "completed", (
                f"Step {step_key} should not be completed after material_fetch failure"
            )


# ---------------------------------------------------------------------------
# Test 3: Artifact file endpoint content-type (no FFmpeg needed)
# ---------------------------------------------------------------------------

class TestArtifactFileEndpointContentType:
    """Verify /file endpoint returns correct content-type headers."""

    def test_artifact_file_endpoint_content_type(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        data = _create_task(client, topic="Content type test")
        task_id = data["task_id"]

        # Write a fake MP4 file on disk and register it
        video_dir = tmp_path / "artifacts" / task_id / "video_compose"
        video_dir.mkdir(parents=True, exist_ok=True)
        video_file = video_dir / "output.mp4"
        video_file.write_bytes(b"\x00\x00\x00 ftypisom" + b"\x00" * 100)

        store = client.app.state.store
        store.add_artifact(
            task_id=task_id,
            step_key="video_compose",
            artifact_type=ArtifactType.final_video,
            storage_ref=str(video_file),
            metadata={"kind": "final_video", "duration_seconds": 10},
        )

        # Get the artifact ID
        arts = store.list_artifacts(task_id)
        final_video = [a for a in arts if a.artifact_type == ArtifactType.final_video]
        assert len(final_video) >= 1
        artifact_id = final_video[-1].id

        # Hit /file endpoint
        resp = client.get(f"/api/video-tasks/{task_id}/artifacts/{artifact_id}/file")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "video/mp4"


# ---------------------------------------------------------------------------
# Test 4: SRT artifact content endpoint (no FFmpeg needed)
# ---------------------------------------------------------------------------

class TestSrtArtifactContentEndpoint:
    """Verify SRT files are served as text content via /content endpoint."""

    def test_srt_artifact_content_endpoint(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        data = _create_task(client, topic="SRT content test")
        task_id = data["task_id"]

        # Write a fake SRT file
        srt_dir = tmp_path / "artifacts" / task_id / "subtitle"
        srt_dir.mkdir(parents=True, exist_ok=True)
        srt_file = srt_dir / "subtitles.srt"
        srt_content = (
            "1\n"
            "00:00:00,000 --> 00:00:05,000\n"
            "Did you know that sleep boosts memory?\n\n"
            "2\n"
            "00:00:05,000 --> 00:00:13,000\n"
            "Recent studies show learning.\n\n"
        )
        srt_file.write_text(srt_content, encoding="utf-8")

        store = client.app.state.store
        store.add_artifact(
            task_id=task_id,
            step_key="subtitle",
            artifact_type=ArtifactType.subtitle,
            storage_ref=str(srt_file),
            metadata={"kind": "subtitle"},
        )

        arts = store.list_artifacts(task_id)
        srt_arts = [a for a in arts if a.artifact_type == ArtifactType.subtitle]
        assert len(srt_arts) >= 1
        artifact_id = srt_arts[-1].id

        resp = client.get(f"/api/video-tasks/{task_id}/artifacts/{artifact_id}/content")
        assert resp.status_code == 200
        content = resp.json()["content"]
        assert "content" in content
        assert "sleep boosts memory" in content["content"]


# ---------------------------------------------------------------------------
# Test 5 & 6: Full pipeline E2E with mocked TTS (requires FFmpeg)
# ---------------------------------------------------------------------------

def _generate_silent_mp3_via_ffmpeg(duration: float = 1.0) -> bytes:
    """Generate a minimal silent MP3 audio file using FFmpeg."""
    import subprocess
    result = subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "64k",
            "-f", "mp3", "-y", "pipe:1",
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr.decode()}")
    return result.stdout


def _make_mock_voiceover_result(
    artifact_store: ArtifactStore,
    task_id: str,
    segments: list[dict],
) -> dict:
    """Create a realistic voiceover timing result with real MP3 audio files."""
    seg_results: list[dict[str, Any]] = []
    seg_audio_paths: list[str] = []

    for seg in segments:
        seg_index = seg["segment_index"]
        voiceover_text = seg.get("voiceover_text", seg.get("narration", ""))
        duration = seg.get("duration_seconds", 5)

        # Generate real silent MP3 audio
        audio_bytes = _generate_silent_mp3_via_ffmpeg(duration)

        ref = artifact_store.write_file(
            task_id=task_id,
            step_key="voiceover",
            artifact_type="audio",
            filename=f"seg_{seg_index}.mp3",
            content=audio_bytes,
        )

        # Probe actual duration
        from app.src.media.ffmpeg_utils import probe_duration
        actual_duration = probe_duration(ref.storage_ref)

        word_boundaries = [
            {"text": word, "offset_ms": i * 300, "duration_ms": 280}
            for i, word in enumerate(voiceover_text.split()[:5])
        ]

        seg_results.append({
            "segment_index": seg_index,
            "voiceover_text": voiceover_text,
            "segment_audio_ref": ref.storage_ref,
            "duration_seconds": actual_duration,
            "word_boundaries": word_boundaries,
        })
        seg_audio_paths.append(ref.storage_ref)

    # Concat all segment audios into a full voiceover via FFmpeg
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for path in seg_audio_paths:
            f.write(f"file '{path}'\n")
        concat_list_path = f.name

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as out_f:
        output_path = out_f.name

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", concat_list_path, "-c", "copy", output_path],
        capture_output=True, timeout=30, check=True,
    )

    full_audio_bytes = Path(output_path).read_bytes()
    full_ref = artifact_store.write_file(
        task_id=task_id,
        step_key="voiceover",
        artifact_type="audio",
        filename="full_voiceover.mp3",
        content=full_audio_bytes,
    )

    # Cleanup temp files
    Path(concat_list_path).unlink(missing_ok=True)
    Path(output_path).unlink(missing_ok=True)

    total_duration = sum(s["duration_seconds"] for s in seg_results)

    return {
        "segments": seg_results,
        "total_duration_seconds": total_duration,
        "full_audio_ref": full_ref.storage_ref,
    }


def _make_mock_subtitle_result(
    artifact_store: ArtifactStore,
    task_id: str,
    voiceover_timing: dict,
) -> dict:
    """Create a realistic subtitle result with a real SRT file."""
    from app.src.skills.subtitle import _build_srt_entries, _format_srt

    segments = voiceover_timing.get("segments", [])
    entries = _build_srt_entries(segments=segments)
    srt_content = _format_srt(entries)
    srt_bytes = srt_content.encode("utf-8")

    ref = artifact_store.write_file(
        task_id=task_id,
        step_key="subtitle",
        artifact_type="subtitle",
        filename="subs.srt",
        content=srt_bytes,
    )

    return {
        "entry_count": len(entries),
        "total_duration_seconds": voiceover_timing.get("total_duration_seconds", 0.0),
        "source": "edge_tts_timing",
        "srt_ref": ref.storage_ref,
    }


class TestFullPipelineWithMockedTTS:
    """Full pipeline E2E with mocked edge-tts and real FFmpeg.

    Voiceover and subtitle skills are mocked at the STEP_SKILLS level to
    produce real audio/SRT files via FFmpeg. Material extract, match, and
    video_compose skills run with real FFmpeg.
    """

    @requires_ffmpeg_subtitles
    def test_full_pipeline_with_mocked_tts(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Create task with source video, run full pipeline, verify final_video exists."""
        assert TEST_VIDEO_PATH.exists(), f"Test video fixture missing: {TEST_VIDEO_PATH}"

        mock_llm = MagicMock()
        mock_llm.chat.return_value = _script_response()

        storyboard_result = _storyboard_response()
        review_result = _review_response()

        source_video_bytes = TEST_VIDEO_PATH.read_bytes()

        with patch("app.src.workers.step_runner.LLMAdapter.from_env", return_value=mock_llm):
            with patch("app.src.skills.material_fetch.httpx.Client") as mock_httpx:
                mock_resp = MagicMock()
                mock_resp.headers = {
                    "content-type": "video/mp4",
                    "content-length": str(len(source_video_bytes)),
                }
                mock_resp.content = source_video_bytes
                mock_httpx_client = MagicMock()
                mock_httpx_client.get.return_value = mock_resp
                mock_httpx.return_value.__enter__ = MagicMock(return_value=mock_httpx_client)
                mock_httpx.return_value.__exit__ = MagicMock(return_value=False)

                artifact_dir = str(tmp_path / "artifacts")
                app = create_app(db_path=":memory:")
                from app.src.artifacts.store import ArtifactStore
                art_store = ArtifactStore(artifact_dir)
                app.state.artifact_store = art_store
                with TestClient(app) as test_client:
                    body = {
                        "input_kind": "topic",
                        "input_text": "Full pipeline E2E test",
                        "source_links": ["https://example.com/test.mp4"],
                    }
                    resp = test_client.post("/api/video-tasks", json=body)
                    assert resp.status_code == 200
                    task_id = resp.json()["task_id"]

                    from app.src.workers.step_runner import StepRunner
                    store = test_client.app.state.store
                    artifact_store = test_client.app.state.artifact_store
                    runner = StepRunner(
                        store=store,
                        artifact_store=artifact_store,
                        llm_adapter=mock_llm,
                    )

                    # Build mock voiceover/subtitle skill functions that use real FFmpeg
                    voiceover_timing_holder: list[dict] = []

                    def _mock_voiceover(**kw) -> dict:
                        segments = kw["storyboard_segments"]
                        result = _make_mock_voiceover_result(
                            artifact_store=kw["artifact_store"],
                            task_id=kw["task_id"],
                            segments=segments,
                        )
                        voiceover_timing_holder.append(result)
                        return result

                    def _mock_subtitle(**kw) -> dict:
                        return _make_mock_subtitle_result(
                            artifact_store=kw["artifact_store"],
                            task_id=kw["task_id"],
                            voiceover_timing=kw["voiceover_timing"],
                        )

                    with patch.dict(
                        "app.src.workers.step_runner.STEP_SKILLS",
                        {
                            "storyboard": lambda **_kw: storyboard_result,
                            "review_script": lambda **_kw: review_result,
                            "voiceover": _mock_voiceover,
                            "subtitle": _mock_subtitle,
                        },
                    ):
                        runner.run_step(task_id=task_id, step_key="storyboard")
                        runner.run_step(task_id=task_id, step_key="review_script")
                        runner.run_step(task_id=task_id, step_key="voiceover")
                        runner.run_step(task_id=task_id, step_key="material_extract")
                        runner.run_step(task_id=task_id, step_key="material_match")
                        runner.run_step(task_id=task_id, step_key="subtitle")
                        runner.run_step(task_id=task_id, step_key="video_compose")

        # Verify video_compose completed
        detail = test_client.get(f"/api/video-tasks/{task_id}").json()
        steps = {s["step_key"]: s for s in detail["steps"]}

        assert steps["video_compose"]["status"] == "completed", (
            f"video_compose expected completed, got {steps['video_compose']['status']}: "
            f"{steps['video_compose'].get('error_message', '')}"
        )

        # Verify final_video artifact
        arts_resp = test_client.get(f"/api/video-tasks/{task_id}/artifacts")
        assert arts_resp.status_code == 200
        artifacts = arts_resp.json()["artifacts"]
        final_video_arts = [a for a in artifacts if a["artifact_type"] == "final_video"]
        assert len(final_video_arts) >= 1, (
            f"Expected final_video artifact, got types: {[a['artifact_type'] for a in artifacts]}"
        )

        # Verify the file endpoint serves it with correct content type
        fv_artifact = final_video_arts[-1]
        file_resp = test_client.get(
            f"/api/video-tasks/{task_id}/artifacts/{fv_artifact['id']}/file"
        )
        assert file_resp.status_code == 200
        assert file_resp.headers["content-type"] == "video/mp4"
        assert len(file_resp.content) > 0

    @requires_ffmpeg_subtitles
    def test_no_source_videos_fallback(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """No source videos -> fallback mode (solid color background)."""
        mock_llm = MagicMock()
        mock_llm.chat.return_value = _script_response()

        storyboard_result = _storyboard_response()
        review_result = _review_response()

        with patch("app.src.workers.step_runner.LLMAdapter.from_env", return_value=mock_llm):
            artifact_dir = str(tmp_path / "artifacts")
            app = create_app(db_path=":memory:")
            from app.src.artifacts.store import ArtifactStore
            app.state.artifact_store = ArtifactStore(artifact_dir)
            with TestClient(app) as test_client:
                body = {
                    "input_kind": "topic",
                    "input_text": "Fallback mode test",
                    "source_links": [],
                }
                resp = test_client.post("/api/video-tasks", json=body)
                assert resp.status_code == 200
                task_id = resp.json()["task_id"]

                from app.src.workers.step_runner import StepRunner
                store = test_client.app.state.store
                artifact_store = test_client.app.state.artifact_store
                runner = StepRunner(
                    store=store,
                    artifact_store=artifact_store,
                    llm_adapter=mock_llm,
                )

                def _mock_voiceover(**kw) -> dict:
                    segments = kw["storyboard_segments"]
                    return _make_mock_voiceover_result(
                        artifact_store=kw["artifact_store"],
                        task_id=kw["task_id"],
                        segments=segments,
                    )

                def _mock_subtitle(**kw) -> dict:
                    return _make_mock_subtitle_result(
                        artifact_store=kw["artifact_store"],
                        task_id=kw["task_id"],
                        voiceover_timing=kw["voiceover_timing"],
                    )

                with patch.dict(
                    "app.src.workers.step_runner.STEP_SKILLS",
                    {
                        "storyboard": lambda **_kw: storyboard_result,
                        "review_script": lambda **_kw: review_result,
                        "voiceover": _mock_voiceover,
                        "subtitle": _mock_subtitle,
                    },
                ):
                    runner.run_step(task_id=task_id, step_key="storyboard")
                    runner.run_step(task_id=task_id, step_key="review_script")
                    runner.run_step(task_id=task_id, step_key="voiceover")
                    runner.run_step(task_id=task_id, step_key="material_extract")
                    runner.run_step(task_id=task_id, step_key="material_match")
                    runner.run_step(task_id=task_id, step_key="subtitle")
                    runner.run_step(task_id=task_id, step_key="video_compose")

        # Verify video_compose completed
        detail = test_client.get(f"/api/video-tasks/{task_id}").json()
        steps = {s["step_key"]: s for s in detail["steps"]}

        assert steps["video_compose"]["status"] == "completed", (
            f"video_compose expected completed, got {steps['video_compose']['status']}: "
            f"{steps['video_compose'].get('error_message', '')}"
        )

        # Verify final_video artifact exists
        arts_resp = test_client.get(f"/api/video-tasks/{task_id}/artifacts")
        assert arts_resp.status_code == 200
        artifacts = arts_resp.json()["artifacts"]
        final_video_arts = [a for a in artifacts if a["artifact_type"] == "final_video"]
        assert len(final_video_arts) >= 1, (
            f"Expected final_video artifact in fallback mode, got types: "
            f"{[a['artifact_type'] for a in artifacts]}"
        )

        # Verify compose_log has fallback_mode=true
        compose_log_arts = [
            a for a in artifacts
            if a["artifact_type"] == "parsed_json"
            and a.get("metadata", {}).get("kind") == "compose_log"
        ]
        assert len(compose_log_arts) >= 1, "Expected compose_log parsed_json artifact"

        log_resp = test_client.get(
            f"/api/video-tasks/{task_id}/artifacts/{compose_log_arts[-1]['id']}/content"
        )
        assert log_resp.status_code == 200
        compose_log = log_resp.json()["content"]
        assert compose_log.get("fallback_mode") is True, (
            f"Expected fallback_mode=True, got {compose_log.get('fallback_mode')}"
        )
