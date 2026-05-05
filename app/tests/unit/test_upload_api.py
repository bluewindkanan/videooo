"""Feature 003: test upload API + pipeline resume."""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.src.domain.models import TaskStatus
from app.src.server.main import create_app
from app.src.artifacts.store import ArtifactStore


def _create_waiting_task(client: TestClient) -> str:
    """Create a task that ends up in waiting_for_material state."""
    resp = client.post("/api/video-tasks", json={
        "input_kind": "topic",
        "input_text": "test upload",
        "source_links": ["https://unreachable.example.com/bad.mp4"],
    })
    return resp.json()["task_id"]


class TestUploadAPI:
    def test_upload_to_waiting_task_accepted(self, tmp_path: Path) -> None:
        app = create_app(db_path=":memory:")
        app.state.artifact_store = ArtifactStore(str(tmp_path / "art"))
        with patch("app.src.skills.material_fetch.httpx.Client") as mock_cls:
            import httpx
            mock_c = MagicMock()
            mock_c.get.side_effect = httpx.ConnectError("fail")
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_c)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            client = TestClient(app)
            tid = _create_waiting_task(client)

        # Task should be waiting_for_material
        detail = client.get(f"/api/video-tasks/{tid}").json()
        assert detail["task"]["status"] == "waiting_for_material"

        # Upload a file
        upload_resp = client.post(
            f"/api/video-tasks/{tid}/materials",
            files={"file": ("clip.mp4", b"\x00\x01\x02" * 100, "video/mp4")},
        )
        assert upload_resp.status_code == 200
        body = upload_resp.json()
        assert body["accepted"] is True

    def test_upload_resumes_pipeline(self, tmp_path: Path) -> None:
        app = create_app(db_path=":memory:")
        app.state.artifact_store = ArtifactStore(str(tmp_path / "art"))
        with patch("app.src.skills.material_fetch.httpx.Client") as mock_cls:
            import httpx
            mock_c = MagicMock()
            mock_c.get.side_effect = httpx.ConnectError("fail")
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_c)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            client = TestClient(app)
            tid = _create_waiting_task(client)

        # Mock LLM for resumed pipeline
        # The LLM adapter is already mocked via the app's default behavior

        upload_resp = client.post(
            f"/api/video-tasks/{tid}/materials",
            files={"file": ("video.mp4", b"\x00" * 50, "video/mp4")},
        )
        assert upload_resp.status_code == 200

        # Task should have resumed and completed pipeline
        detail = client.get(f"/api/video-tasks/{tid}").json()
        assert detail["task"]["status"] != "waiting_for_material"

    def test_upload_to_non_waiting_rejected(self, tmp_path: Path) -> None:
        app = create_app(db_path=":memory:")
        app.state.artifact_store = ArtifactStore(str(tmp_path / "art"))
        with patch("app.src.skills.material_fetch.httpx.Client") as mock_cls:
            mock_resp = MagicMock()
            mock_resp.headers = {"content-type": "video/mp4", "content-length": "50"}
            mock_resp.content = b"\x00" * 50
            mock_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(get=MagicMock(return_value=mock_resp)))
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            client = TestClient(app)
            resp = client.post("/api/video-tasks", json={
                "input_kind": "topic",
                "input_text": "test",
                "source_links": ["https://example.com/good.mp4"],
            })
            tid = resp.json()["task_id"]

        # Task should NOT be waiting (download succeeded)
        detail = client.get(f"/api/video-tasks/{tid}").json()
        assert detail["task"]["status"] != "waiting_for_material"

        # Upload should be rejected
        upload_resp = client.post(
            f"/api/video-tasks/{tid}/materials",
            files={"file": ("file.mp4", b"data", "video/mp4")},
        )
        assert upload_resp.status_code == 409

    def test_upload_wrong_extension_rejected(self, tmp_path: Path) -> None:
        app = create_app(db_path=":memory:")
        app.state.artifact_store = ArtifactStore(str(tmp_path / "art"))
        with patch("app.src.skills.material_fetch.httpx.Client") as mock_cls:
            import httpx
            mock_c = MagicMock()
            mock_c.get.side_effect = httpx.ConnectError("fail")
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_c)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            client = TestClient(app)
            tid = _create_waiting_task(client)

        upload_resp = client.post(
            f"/api/video-tasks/{tid}/materials",
            files={"file": ("malware.exe", b"bad", "application/octet-stream")},
        )
        assert upload_resp.status_code == 422
