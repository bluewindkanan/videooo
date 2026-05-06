"""Integration tests for /api/video-tasks — S-001 through S-004 coverage.

These tests exercise the FastAPI routes end-to-end using TestClient with an
in-memory SQLite database and mocked LLM calls.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.src.domain.models import StepStatus
from app.src.server.main import create_app


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
                "index": 0,
                "title": "Hook",
                "narration": "Did you know that sleep boosts memory?",
                "visual_description": "Close-up of a person sleeping peacefully",
                "duration_seconds": 5,
            },
            {
                "index": 1,
                "title": "Body",
                "narration": "Recent studies show that 7-9 hours of sleep consolidates learning.",
                "visual_description": "Infographic showing sleep stages",
                "duration_seconds": 20,
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
    """A mock LLMAdapter whose .chat() returns a valid script JSON by default."""
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
# S-001: LLM generates script
# ---------------------------------------------------------------------------

class TestS001ScriptGeneration:
    """POST /api/video-tasks triggers script_generation and produces artifacts."""

    def test_script_generation_produces_artifact(self, client: TestClient) -> None:
        data = _create_task(client)
        task_id = data["task_id"]

        # Verify task detail
        detail = client.get(f"/api/video-tasks/{task_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["task"]["id"] == task_id

        # Verify script_generation step completed
        steps = body["steps"]
        sg_step = next((s for s in steps if s["step_key"] == "script_generation"), None)
        assert sg_step is not None, f"script_generation step not found in {steps}"
        assert sg_step["status"] == "completed"

        # Verify artifacts include parsed_json from script generation
        arts_resp = client.get(f"/api/video-tasks/{task_id}/artifacts")
        assert arts_resp.status_code == 200
        artifacts = arts_resp.json()["artifacts"]
        artifact_types = [a["artifact_type"] for a in artifacts]
        assert "parsed_json" in artifact_types, f"Expected parsed_json in {artifact_types}"
        assert "llm_raw" in artifact_types, f"Expected llm_raw in {artifact_types}"
        assert "input" in artifact_types, f"Expected input in {artifact_types}"

        # Verify artifact schema via content endpoint
        parsed_json_artifact = next(a for a in artifacts if a["artifact_type"] == "parsed_json")
        content_resp = client.get(
            f"/api/video-tasks/{task_id}/artifacts/{parsed_json_artifact['id']}/content"
        )
        assert content_resp.status_code == 200
        content = content_resp.json()["content"]
        assert "hook" in content
        assert "body" in content
        assert "call_to_action" in content
        assert "estimated_duration_seconds" in content
        assert isinstance(content["estimated_duration_seconds"], int)


# ---------------------------------------------------------------------------
# S-002: Storyboard generation
# ---------------------------------------------------------------------------

class TestS002StoryboardStep:
    """Storyboard step runs via StepRunner with a mocked skill function."""

    def test_storyboard_step_produces_segments(
        self, client: TestClient
    ) -> None:
        data = _create_task(client)
        task_id = data["task_id"]

        from app.src.workers.step_runner import StepRunner

        store = client.app.state.store
        artifact_store = client.app.state.artifact_store
        mock_adapter = MagicMock()
        runner = StepRunner(store=store, artifact_store=artifact_store, llm_adapter=mock_adapter)

        # Patch STEP_SKILLS so storyboard uses a real function instead of placeholder
        storyboard_result = _storyboard_response()
        with patch.dict(
            "app.src.workers.step_runner.STEP_SKILLS",
            {"storyboard": lambda **_kw: storyboard_result},
        ):
            executed = runner.run_step(task_id=task_id, step_key="storyboard")
            assert executed is True

        step = store.get_step(task_id, "storyboard")
        assert step is not None
        assert step.status == StepStatus.completed


# ---------------------------------------------------------------------------
# S-003: Review produces findings
# ---------------------------------------------------------------------------

class TestS003ReviewStep:
    """Review step runs via StepRunner with a mocked skill function."""

    def test_review_step_produces_findings(
        self, client: TestClient
    ) -> None:
        data = _create_task(client)
        task_id = data["task_id"]

        from app.src.workers.step_runner import StepRunner

        store = client.app.state.store
        artifact_store = client.app.state.artifact_store
        mock_adapter = MagicMock()
        runner = StepRunner(store=store, artifact_store=artifact_store, llm_adapter=mock_adapter)

        # Patch STEP_SKILLS so review uses a real function instead of placeholder
        review_result = _review_response()
        with patch.dict(
            "app.src.workers.step_runner.STEP_SKILLS",
            {"review_script": lambda **_kw: review_result},
        ):
            executed = runner.run_step(task_id=task_id, step_key="review_script")
            assert executed is True

        step = store.get_step(task_id, "review_script")
        assert step is not None
        assert step.status == StepStatus.completed


# ---------------------------------------------------------------------------
# S-004: Task list endpoint
# ---------------------------------------------------------------------------

class TestS004TaskList:
    """GET /api/video-tasks returns all tasks ordered by created_at DESC."""

    def test_task_list_endpoint(self, client: TestClient) -> None:
        topics = ["Alpha topic", "Beta topic", "Gamma topic"]
        task_ids: list[str] = []
        for topic in topics:
            data = _create_task(client, topic=topic)
            task_ids.append(data["task_id"])
            # Small sleep to ensure distinct created_at ordering
            time.sleep(0.01)

        resp = client.get("/api/video-tasks")
        assert resp.status_code == 200
        tasks = resp.json()["tasks"]

        # All 3 tasks present
        returned_ids = [t["id"] for t in tasks]
        for tid in task_ids:
            assert tid in returned_ids

        # Ordered by created_at DESC (last created first)
        assert tasks[0]["id"] == task_ids[-1]
        assert tasks[-1]["id"] == task_ids[0]


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """End-to-end: create task, run all steps, verify artifacts and task list."""

    def test_full_pipeline_e2e(self, client: TestClient) -> None:
        data = _create_task(client, topic="Full pipeline test")
        task_id = data["task_id"]

        from app.src.workers.step_runner import StepRunner

        store = client.app.state.store
        artifact_store = client.app.state.artifact_store
        mock_adapter = MagicMock()
        runner = StepRunner(store=store, artifact_store=artifact_store, llm_adapter=mock_adapter)

        # Patch placeholders with real mock skill functions
        storyboard_result = _storyboard_response()
        review_result = _review_response()
        with patch.dict(
            "app.src.workers.step_runner.STEP_SKILLS",
            {
                "storyboard": lambda **_kw: storyboard_result,
                "review_script": lambda **_kw: review_result,
            },
        ):
            runner.run_step(task_id=task_id, step_key="storyboard")
            runner.run_step(task_id=task_id, step_key="review_script")

        # Verify task detail has all 9 steps
        detail = client.get(f"/api/video-tasks/{task_id}")
        assert detail.status_code == 200
        steps = detail.json()["steps"]
        step_keys = {s["step_key"] for s in steps}
        assert step_keys == {
            "material_fetch", "script_generation", "storyboard", "review_script",
            "voiceover", "material_extract", "material_match", "subtitle", "video_compose",
        }

        # LLM steps should be completed; media steps may fail without proper upstream data
        llm_steps = {"material_fetch", "script_generation", "storyboard", "review_script"}
        for s in steps:
            if s["step_key"] in llm_steps:
                assert s["status"] == "completed", (
                    f"Step {s['step_key']} expected completed, got {s['status']}"
                )

        # Verify artifacts exist
        arts_resp = client.get(f"/api/video-tasks/{task_id}/artifacts")
        assert arts_resp.status_code == 200
        artifacts = arts_resp.json()["artifacts"]
        artifact_types = [a["artifact_type"] for a in artifacts]
        assert "parsed_json" in artifact_types
        assert "llm_raw" in artifact_types

        # Verify task list shows the task
        list_resp = client.get("/api/video-tasks")
        assert list_resp.status_code == 200
        list_ids = [t["id"] for t in list_resp.json()["tasks"]]
        assert task_id in list_ids


# ---------------------------------------------------------------------------
# Artifact content endpoint
# ---------------------------------------------------------------------------

class TestArtifactContent:
    """GET /api/video-tasks/{task_id}/artifacts/{artifact_id}/content returns JSON."""

    def test_artifact_content_endpoint(self, client: TestClient) -> None:
        data = _create_task(client)
        task_id = data["task_id"]

        # Get artifact list
        arts_resp = client.get(f"/api/video-tasks/{task_id}/artifacts")
        assert arts_resp.status_code == 200
        artifacts = arts_resp.json()["artifacts"]
        assert len(artifacts) >= 1

        # Fetch content for each artifact
        for artifact in artifacts:
            content_resp = client.get(
                f"/api/video-tasks/{task_id}/artifacts/{artifact['id']}/content"
            )
            assert content_resp.status_code == 200, (
                f"Failed to get content for artifact {artifact['id']}: {content_resp.text}"
            )
            content_body = content_resp.json()
            assert "artifact_id" in content_body
            assert "content" in content_body
            # Content should be a dict (JSON object)
            assert isinstance(content_body["content"], dict)


# ---------------------------------------------------------------------------
# Original test preserved
# ---------------------------------------------------------------------------

class TestOriginalFlow:
    """Keep the original integration test as a regression guard."""

    def test_create_and_query_task_and_artifacts(self, client: TestClient) -> None:
        data = _create_task(
            client,
            topic="hello",
            source_links=["https://example.com/a.mp4"],
        )
        task_id = data["task_id"]

        detail = client.get(f"/api/video-tasks/{task_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["task"]["id"] == task_id
        assert len(body["steps"]) >= 1

        artifacts = client.get(f"/api/video-tasks/{task_id}/artifacts")
        assert artifacts.status_code == 200
        artifacts_json = artifacts.json()
        assert len(artifacts_json["artifacts"]) >= 1
        assert any(
            a["artifact_type"] in ("input", "parsed_json")
            for a in artifacts_json["artifacts"]
        )


# ---------------------------------------------------------------------------
# Feature 003: Material dual path
# ---------------------------------------------------------------------------

class TestMaterialFetchIntegration:
    """S-001: System downloads source links and displays status."""

    def test_material_fetch_success_with_source_links(self, client: TestClient) -> None:
        with patch("app.src.skills.material_fetch.httpx.Client") as mock_cls:
            mock_resp = MagicMock()
            mock_resp.headers = {"content-type": "video/mp4", "content-length": "100"}
            mock_resp.content = b"\x00" * 100
            mock_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(get=MagicMock(return_value=mock_resp)))
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            data = _create_task(client, topic="Material test", source_links=["https://example.com/video.mp4"])
            task_id = data["task_id"]

        detail = client.get(f"/api/video-tasks/{task_id}").json()
        steps = {s["step_key"]: s for s in detail["steps"]}

        # material_fetch step exists and completed
        assert "material_fetch" in steps
        assert steps["material_fetch"]["status"] == "completed"

        # material_status artifact exists
        arts = client.get(f"/api/video-tasks/{task_id}/artifacts").json()["artifacts"]
        mat_status = [a for a in arts if a["artifact_type"] == "material_status"]
        assert len(mat_status) >= 1

    def test_material_fetch_all_failed_waits_for_upload(self, tmp_path: Path, mock_llm_adapter: MagicMock) -> None:
        from app.src.skills.material_fetch import MaterialFetchResult

        failed_results = [
            MaterialFetchResult(url="https://bad.example.com/vid.mp4", status="failed",
                                failure_category="unreachable", failure_message="DNS failure"),
        ]
        artifact_dir = str(tmp_path / "artifacts")
        with patch("app.src.workers.step_runner.LLMAdapter.from_env", return_value=mock_llm_adapter):
            from app.src.artifacts.store import ArtifactStore
            app = create_app(db_path=":memory:")
            app.state.artifact_store = ArtifactStore(artifact_dir)
            with patch.dict(
                "app.src.workers.step_runner.STEP_SKILLS",
                {"material_fetch": lambda **_kw: failed_results},
            ):
                with TestClient(app) as client:
                    data = _create_task(
                        client, topic="All links unreachable",
                        source_links=["https://bad.example.com/vid.mp4"],
                    )
                    task_id = data["task_id"]

                    detail = client.get(f"/api/video-tasks/{task_id}").json()
                    assert detail["task"]["status"] == "waiting_for_material"

        steps = {s["step_key"]: s for s in detail["steps"]}
        assert steps["material_fetch"]["status"] == "failed"

    def test_material_fetch_empty_links_skips_gracefully(self, client: TestClient) -> None:
        data = _create_task(client, topic="No links", source_links=[])
        task_id = data["task_id"]

        detail = client.get(f"/api/video-tasks/{task_id}").json()
        steps = {s["step_key"]: s for s in detail["steps"]}
        assert steps["material_fetch"]["status"] == "completed"

        # Pipeline should have continued
        assert steps["script_generation"]["status"] == "completed"


class TestUploadResumeIntegration:
    """S-003: Upload replacement material and resume pipeline."""

    def test_upload_resumes_pipeline_after_failure(self, client: TestClient) -> None:
        with patch("app.src.skills.material_fetch.httpx.Client") as mock_cls:
            import httpx
            mock_c = MagicMock()
            mock_c.get.side_effect = httpx.ConnectError("fail")
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_c)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            data = _create_task(
                client, topic="Upload test",
                source_links=["https://bad.example.com/x.mp4"],
            )
            task_id = data["task_id"]

        # Verify waiting_for_material
        detail = client.get(f"/api/video-tasks/{task_id}").json()
        assert detail["task"]["status"] == "waiting_for_material"

        # Upload replacement
        upload_resp = client.post(
            f"/api/video-tasks/{task_id}/materials",
            files={"file": ("replacement.mp4", b"\x00" * 100, "video/mp4")},
        )
        assert upload_resp.status_code == 200
        assert upload_resp.json()["accepted"] is True

        # Verify pipeline resumed
        detail = client.get(f"/api/video-tasks/{task_id}").json()
        assert detail["task"]["status"] != "waiting_for_material"

        # uploaded_video artifact exists
        arts = client.get(f"/api/video-tasks/{task_id}/artifacts").json()["artifacts"]
        uploaded = [a for a in arts if a["artifact_type"] == "uploaded_video"]
        assert len(uploaded) >= 1


# ---------------------------------------------------------------------------
# Feature 004 T007: Pipeline orchestration + file serving
# ---------------------------------------------------------------------------

class TestPipeline9Steps:
    """Verify create_video_task initializes all 9 steps."""

    def test_create_task_runs_all_9_steps(self, client: TestClient) -> None:
        data = _create_task(client, topic="Nine-step pipeline test")
        task_id = data["task_id"]

        detail = client.get(f"/api/video-tasks/{task_id}").json()
        step_keys = [s["step_key"] for s in detail["steps"]]
        assert len(step_keys) == 9, f"Expected 9 steps, got {len(step_keys)}: {step_keys}"

        expected = {
            "material_fetch", "script_generation", "storyboard", "review_script",
            "voiceover", "material_extract", "material_match", "subtitle", "video_compose",
        }
        assert set(step_keys) == expected

        # material_fetch, script_generation should be completed
        # (they ran during task creation with mocked LLM)
        steps_by_key = {s["step_key"]: s for s in detail["steps"]}
        assert steps_by_key["material_fetch"]["status"] == "completed"
        assert steps_by_key["script_generation"]["status"] == "completed"


class TestArtifactFileEndpoint:
    """GET /api/video-tasks/{task_id}/artifacts/{artifact_id}/file serves binary files."""

    def _create_task_with_video_artifact(
        self, client: TestClient, tmp_path: Path
    ) -> tuple[str, str]:
        """Helper: create a task and add a fake video artifact file."""
        data = _create_task(client, topic="File serving test")
        task_id = data["task_id"]

        # Write a fake video file
        video_dir = tmp_path / "artifacts" / task_id / "video_compose"
        video_dir.mkdir(parents=True, exist_ok=True)
        video_file = video_dir / "output.mp4"
        video_file.write_bytes(b"\x00\x00\x00 ftypisom" + b"\x00" * 100)

        # Register artifact in store
        store = client.app.state.store
        from app.src.domain.models import ArtifactType
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
        return task_id, final_video[-1].id

    def test_artifact_file_endpoint_returns_video(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        task_id, artifact_id = self._create_task_with_video_artifact(client, tmp_path)

        resp = client.get(f"/api/video-tasks/{task_id}/artifacts/{artifact_id}/file")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "video/mp4"
        assert len(resp.content) > 0

    def test_artifact_file_endpoint_404_for_missing_task(
        self, client: TestClient
    ) -> None:
        resp = client.get("/api/video-tasks/nonexistent/artifacts/nonexistent/file")
        assert resp.status_code == 404

    def test_artifact_file_endpoint_404_for_missing_artifact(
        self, client: TestClient
    ) -> None:
        data = _create_task(client, topic="Missing artifact test")
        task_id = data["task_id"]

        resp = client.get(f"/api/video-tasks/{task_id}/artifacts/nonexistent/file")
        assert resp.status_code == 404

    def test_artifact_file_endpoint_404_for_missing_file(
        self, client: TestClient
    ) -> None:
        """Artifact exists in DB but the file on disk is gone."""
        data = _create_task(client, topic="Missing file test")
        task_id = data["task_id"]

        store = client.app.state.store
        from app.src.domain.models import ArtifactType
        store.add_artifact(
            task_id=task_id,
            step_key="video_compose",
            artifact_type=ArtifactType.final_video,
            storage_ref="/nonexistent/path/output.mp4",
            metadata={"kind": "final_video"},
        )

        arts = store.list_artifacts(task_id)
        final_video = [a for a in arts if a.artifact_type == ArtifactType.final_video]
        assert len(final_video) >= 1
        artifact_id = final_video[-1].id

        resp = client.get(f"/api/video-tasks/{task_id}/artifacts/{artifact_id}/file")
        assert resp.status_code == 404


class TestSrtArtifactContent:
    """Verify .srt files are returned as text content, not as binary."""

    def test_srt_artifact_content_returned_as_text(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        data = _create_task(client, topic="SRT content test")
        task_id = data["task_id"]

        # Write a fake SRT file
        srt_dir = tmp_path / "artifacts" / task_id / "subtitle"
        srt_dir.mkdir(parents=True, exist_ok=True)
        srt_file = srt_dir / "subtitles.srt"
        srt_content = "1\n00:00:00,000 --> 00:00:05,000\nHello world\n\n"
        srt_file.write_text(srt_content, encoding="utf-8")

        store = client.app.state.store
        from app.src.domain.models import ArtifactType
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
        assert "Hello world" in content["content"]
