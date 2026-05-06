"""Feature 004: test FFmpeg utility functions."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from app.src.media.ffmpeg_utils import check_ffmpeg_available, probe_duration, run_ffmpeg


class TestCheckFfmpegAvailable:
    def test_returns_true_when_ffmpeg_exists(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 6.0\n"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            available, version_or_error = check_ffmpeg_available()
            assert available is True
            assert "ffmpeg version" in version_or_error
            mock_run.assert_called_once_with(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

    def test_returns_false_when_ffmpeg_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError("No ffmpeg")):
            available, version_or_error = check_ffmpeg_available()
            assert available is False
            assert "not found" in version_or_error.lower()

    def test_returns_false_on_timeout(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 10)):
            available, version_or_error = check_ffmpeg_available()
            assert available is False
            assert "timeout" in version_or_error.lower() or "error" in version_or_error.lower()


class TestProbeDuration:
    def test_returns_duration_from_ffprobe(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "15.500000"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            duration = probe_duration("/path/to/video.mp4")
            assert duration == 15.5
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "ffprobe" in call_args[0][0][0]

    def test_raises_on_ffprobe_failure(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "No such file"
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError):
                probe_duration("/nonexistent/file.mp4")


class TestRunFfmpeg:
    def test_returns_completed_process_on_success(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = run_ffmpeg(["-i", "input.mp4", "output.mp4"])
            assert result.returncode == 0
            mock_run.assert_called_once()

    def test_raises_on_nonzero_exit(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Conversion failed"
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="FFmpeg failed"):
                run_ffmpeg(["-i", "bad.mp4", "out.mp4"])

    def test_passes_args_correctly(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_ffmpeg(["-i", "in.mp4", "-c:v", "libx264", "out.mp4"])
            call_args = mock_run.call_args[0][0]
            assert call_args == ["ffmpeg", "-i", "in.mp4", "-c:v", "libx264", "out.mp4"]

    def test_uses_timeout(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_ffmpeg(["-i", "in.mp4", "out.mp4"])
            assert mock_run.call_args[1].get("timeout") is not None
