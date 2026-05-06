"""FFmpeg utility functions for media processing."""
from __future__ import annotations

import subprocess


FFMPEG_TIMEOUT = 300  # 5 minutes default timeout


def check_ffmpeg_available() -> tuple[bool, str]:
    """Check if FFmpeg is available on the system.

    Returns:
        Tuple of (available, version_string_or_error_message).
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            first_line = result.stdout.split("\n")[0]
            return (True, first_line)
        return (False, f"FFmpeg returned exit code {result.returncode}")
    except FileNotFoundError:
        return (False, "FFmpeg not found: ensure ffmpeg is installed and on PATH")
    except subprocess.TimeoutExpired:
        return (False, "FFmpeg version check timeout")


def probe_duration(path: str) -> float:
    """Probe media file duration using ffprobe.

    Args:
        path: Path to the media file.

    Returns:
        Duration in seconds as a float.

    Raises:
        RuntimeError: If ffprobe fails or file is not found.
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True,
        text=True,
        timeout=FFMPEG_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return float(result.stdout.strip())


def run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    """Run an FFmpeg command with unified error handling.

    Args:
        args: FFmpeg arguments (without the leading 'ffmpeg' command).

    Returns:
        CompletedProcess on success.

    Raises:
        RuntimeError: If FFmpeg returns a non-zero exit code.
    """
    cmd = ["ffmpeg"] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=FFMPEG_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result
