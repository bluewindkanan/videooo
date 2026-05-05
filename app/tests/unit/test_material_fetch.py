"""Unit tests for material_fetch skill — download + error categorization."""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.src.artifacts.store import ArtifactStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_store() -> MagicMock:
    """Create a mock ArtifactStore with a write_file method.

    Note: write_file is added by T001. Since T002 may run in parallel,
    we do NOT use spec=ArtifactStore so the mock allows write_file even
    when ArtifactStore does not yet have that method.
    """
    store = MagicMock()
    store.write_file.return_value = MagicMock(storage_ref="/fake/path/video.mp4")
    return store


def _mock_response(
    *,
    status_code: int = 200,
    content_type: str = "video/mp4",
    content: bytes = b"\x00\x00\x00\x20ftypisom" + b"\x00" * 1000,
    headers: dict | None = None,
) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = {"content-type": content_type}
    if headers:
        resp.headers.update(headers)
    resp.content = content
    resp.read = MagicMock()
    return resp


VALID_VIDEO_BYTES = b"\x00\x00\x00\x20ftypisom" + b"\x00" * 10000


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestSuccessfulDownload:
    """Verify a valid video download produces a success result."""

    @patch("app.src.skills.material_fetch.httpx.Client")
    def test_successful_download(self, mock_client_cls: MagicMock) -> None:
        from app.src.skills.material_fetch import (
            MaterialFetchResult,
            run_material_fetch,
        )

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _mock_response(content=VALID_VIDEO_BYTES)

        store = _make_mock_store()
        results = run_material_fetch(
            source_links=["https://example.com/video.mp4"],
            artifact_store=store,
            task_id="task-001",
        )

        assert len(results) == 1
        result = results[0]
        assert result.url == "https://example.com/video.mp4"
        assert result.status == "success"
        assert result.failure_category is None
        assert result.failure_message is None
        assert result.storage_ref is not None
        assert result.file_size == len(VALID_VIDEO_BYTES)
        assert result.content_type == "video/mp4"
        store.write_file.assert_called_once()


class TestUnreachableUrl:
    """Verify ConnectError / ConnectTimeout produces unreachable category."""

    @patch("app.src.skills.material_fetch.httpx.Client")
    def test_unreachable_url(self, mock_client_cls: MagicMock) -> None:
        from app.src.skills.material_fetch import run_material_fetch

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        store = _make_mock_store()
        results = run_material_fetch(
            source_links=["https://unreachable.example.com/video.mp4"],
            artifact_store=store,
            task_id="task-002",
        )

        assert len(results) == 1
        assert results[0].status == "failed"
        assert results[0].failure_category == "unreachable"
        assert results[0].failure_message is not None
        assert "Connection refused" in results[0].failure_message


class TestTimeout:
    """Verify ReadTimeout produces timeout category."""

    @patch("app.src.skills.material_fetch.httpx.Client")
    def test_timeout(self, mock_client_cls: MagicMock) -> None:
        from app.src.skills.material_fetch import run_material_fetch

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ReadTimeout("Read timed out")

        store = _make_mock_store()
        results = run_material_fetch(
            source_links=["https://slow.example.com/video.mp4"],
            artifact_store=store,
            task_id="task-003",
        )

        assert len(results) == 1
        assert results[0].status == "failed"
        assert results[0].failure_category == "timeout"
        assert results[0].failure_message is not None


class TestUnsupportedFormat:
    """Verify non-video Content-Type produces unsupported_format category."""

    @patch("app.src.skills.material_fetch.httpx.Client")
    def test_unsupported_format(self, mock_client_cls: MagicMock) -> None:
        from app.src.skills.material_fetch import run_material_fetch

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _mock_response(
            content_type="text/html",
            content=b"<html><body>Error page</body></html>",
        )

        store = _make_mock_store()
        results = run_material_fetch(
            source_links=["https://example.com/page.html"],
            artifact_store=store,
            task_id="task-004",
        )

        assert len(results) == 1
        assert results[0].status == "failed"
        assert results[0].failure_category == "unsupported_format"
        assert results[0].failure_message is not None


class TestSizeExceeded:
    """Verify oversized Content-Length produces size_exceeded category."""

    @patch("app.src.skills.material_fetch.httpx.Client")
    def test_size_exceeded(self, mock_client_cls: MagicMock) -> None:
        from app.src.skills.material_fetch import MAX_FILE_SIZE, run_material_fetch

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = _mock_response(
            content_type="video/mp4",
            headers={"content-length": str(MAX_FILE_SIZE + 1)},
            content=VALID_VIDEO_BYTES,
        )

        store = _make_mock_store()
        results = run_material_fetch(
            source_links=["https://example.com/huge-video.mp4"],
            artifact_store=store,
            task_id="task-005",
        )

        assert len(results) == 1
        assert results[0].status == "failed"
        assert results[0].failure_category == "size_exceeded"
        assert results[0].failure_message is not None


class TestPlatformRestriction:
    """Verify 200 with small non-video body produces platform_restriction category."""

    @patch("app.src.skills.material_fetch.httpx.Client")
    def test_platform_restriction(self, mock_client_cls: MagicMock) -> None:
        from app.src.skills.material_fetch import run_material_fetch

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        # 200 response, small body, non-video content type -> auth wall
        mock_client.get.return_value = _mock_response(
            content_type="text/html",
            content=b'<html><body>Please log in</body></html>',
        )

        store = _make_mock_store()
        results = run_material_fetch(
            source_links=["https://restricted.example.com/video.mp4"],
            artifact_store=store,
            task_id="task-006",
        )

        assert len(results) == 1
        assert results[0].status == "failed"
        assert results[0].failure_category == "platform_restriction"
        assert results[0].failure_message is not None


class TestEmptySourceLinks:
    """Empty source_links returns empty list immediately."""

    def test_empty_source_links(self) -> None:
        from app.src.skills.material_fetch import run_material_fetch

        store = _make_mock_store()
        results = run_material_fetch(
            source_links=[],
            artifact_store=store,
            task_id="task-007",
        )

        assert results == []
        store.write_file.assert_not_called()


class TestMixedResults:
    """Some succeed, some fail — all processed independently."""

    @patch("app.src.skills.material_fetch.httpx.Client")
    def test_mixed_results(self, mock_client_cls: MagicMock) -> None:
        from app.src.skills.material_fetch import run_material_fetch

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        # First URL succeeds, second fails (unreachable), third fails (unsupported format)
        mock_client.get.side_effect = [
            _mock_response(content=VALID_VIDEO_BYTES),
            httpx.ConnectError("DNS failure"),
            _mock_response(
                content_type="text/html",
                content=b"<html>Error</html>",
            ),
        ]

        store = _make_mock_store()
        results = run_material_fetch(
            source_links=[
                "https://example.com/good.mp4",
                "https://down.example.com/video.mp4",
                "https://example.com/bad.html",
            ],
            artifact_store=store,
            task_id="task-008",
        )

        assert len(results) == 3

        # First: success
        assert results[0].status == "success"
        assert results[0].failure_category is None
        assert results[0].storage_ref is not None

        # Second: unreachable
        assert results[1].status == "failed"
        assert results[1].failure_category == "unreachable"

        # Third: unsupported_format or platform_restriction (small html body)
        assert results[2].status == "failed"
        assert results[2].failure_category in ("unsupported_format", "platform_restriction")

        # Only one file should have been written (the success)
        assert store.write_file.call_count == 1


class TestConnectTimeoutIsUnreachable:
    """ConnectTimeout should be categorized as unreachable."""

    @patch("app.src.skills.material_fetch.httpx.Client")
    def test_connect_timeout(self, mock_client_cls: MagicMock) -> None:
        from app.src.skills.material_fetch import run_material_fetch

        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectTimeout("Connect timed out")

        store = _make_mock_store()
        results = run_material_fetch(
            source_links=["https://slow-connect.example.com/video.mp4"],
            artifact_store=store,
            task_id="task-009",
        )

        assert len(results) == 1
        assert results[0].failure_category == "unreachable"
