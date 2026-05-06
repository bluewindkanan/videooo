"""Video compose skill -- FFmpeg-based composition with clips, audio, and subtitles."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from app.src.artifacts.store import ArtifactStore
from app.src.media.ffmpeg_utils import check_ffmpeg_available, run_ffmpeg


class VideoComposeError(Exception):
    """Raised when video composition fails."""


def _build_concat_file(
    *,
    matches: list[dict[str, Any]],
    clips: list[dict[str, Any]],
) -> str:
    """Build a concat demuxer input file from matched segments.

    Returns the path to the temporary concat file.
    """
    # Build a lookup from clip_index to clip data
    clip_by_index = {c["clip_index"]: c for c in clips}

    lines: list[str] = []
    for match in matches:
        for assigned in match.get("assigned_clips", []):
            clip_idx = assigned["clip_index"]
            clip = clip_by_index.get(clip_idx)
            if clip is None:
                continue
            clip_path = clip["storage_ref"]
            lines.append(f"file '{clip_path}'")
            lines.append(f"inpoint {assigned['start_seconds']}")
            lines.append(f"outpoint {assigned['end_seconds']}")

    content = "\n".join(lines) + "\n"

    fd, path = tempfile.mkstemp(suffix=".txt", prefix="ffmpeg_concat_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)

    return path


def _compose_normal(
    *,
    concat_file_path: str,
    full_audio_path: str,
    subtitle_ref: str,
    output_path: str,
    total_duration: float,
) -> None:
    """Run FFmpeg in normal mode: concat clips + audio + subtitle burn-in."""
    subtitle_filter = (
        f"subtitles={subtitle_ref}"
        f":force_style='FontSize=22,PrimaryColour=&Hffffff,FontName=PingFang SC'"
    )

    args = [
        "-f", "concat", "-safe", "0", "-i", concat_file_path,
        "-i", full_audio_path,
        "-vf", subtitle_filter,
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
        "-map", "0:v", "-map", "1:a", "-shortest",
        "-y",
        output_path,
    ]

    try:
        run_ffmpeg(args)
    except RuntimeError:
        # Subtitle font fallback: retry without force_style
        fallback_args = [
            "-f", "concat", "-safe", "0", "-i", concat_file_path,
            "-i", full_audio_path,
            "-vf", f"subtitles={subtitle_ref}",
            "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
            "-map", "0:v", "-map", "1:a", "-shortest",
            "-y",
            output_path,
        ]
        run_ffmpeg(fallback_args)


def _compose_fallback(
    *,
    full_audio_path: str,
    subtitle_ref: str,
    output_path: str,
    total_duration: float,
) -> None:
    """Run FFmpeg in fallback mode: solid color background + audio + subtitle."""
    subtitle_filter = (
        f"subtitles={subtitle_ref}"
        f":force_style='FontSize=22,PrimaryColour=&Hffffff,FontName=PingFang SC'"
    )

    args = [
        "-f", "lavfi", "-i",
        f"color=c=0x1a1a2e:s=1280x720:d={total_duration}:r=30",
        "-i", full_audio_path,
        "-vf", subtitle_filter,
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
        "-shortest", "-y",
        output_path,
    ]

    try:
        run_ffmpeg(args)
    except RuntimeError:
        # Subtitle font fallback
        fallback_args = [
            "-f", "lavfi", "-i",
            f"color=c=0x1a1a2e:s=1280x720:d={total_duration}:r=30",
            "-i", full_audio_path,
            "-vf", f"subtitles={subtitle_ref}",
            "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
            "-shortest", "-y",
            output_path,
        ]
        run_ffmpeg(fallback_args)


def run_video_compose(
    *,
    matched_segments: dict[str, Any],
    voiceover_timing: dict[str, Any],
    subtitle_ref: str,
    clip_manifest: dict[str, Any],
    artifact_store: ArtifactStore,
    task_id: str,
) -> dict[str, Any]:
    """Compose a final video from matched clips, voiceover audio, and subtitles.

    Parameters
    ----------
    matched_segments:
        Output from material_match skill containing matches and fallback_mode.
    voiceover_timing:
        Output from voiceover skill with full_audio_ref and total_duration_seconds.
    subtitle_ref:
        Path to the .srt subtitle file.
    clip_manifest:
        Output from material_extract skill containing clip storage refs.
    artifact_store:
        ArtifactStore for writing the output video.
    task_id:
        Task identifier for artifact organization.

    Returns
    -------
    dict
        Compose log with duration, resolution, flags, and storage_ref.

    Raises
    ------
    VideoComposeError
        If FFmpeg is unavailable or composition fails.
    """
    # Check FFmpeg availability
    available, version_or_error = check_ffmpeg_available()
    if not available:
        raise VideoComposeError(f"FFmpeg not available: {version_or_error}")

    fallback_mode = matched_segments.get("fallback_mode", False)
    full_audio_path = voiceover_timing.get("full_audio_ref", "")
    total_duration = voiceover_timing.get("total_duration_seconds", 0.0)
    matches = matched_segments.get("matches", [])
    clips = clip_manifest.get("clips", [])

    # Create temp output file
    output_fd, output_path = tempfile.mkstemp(suffix=".mp4", prefix="compose_output_")
    os.close(output_fd)

    concat_file_path: str | None = None

    try:
        if not fallback_mode and clips:
            # Normal mode: build concat file from matched segments
            concat_file_path = _build_concat_file(matches=matches, clips=clips)
            _compose_normal(
                concat_file_path=concat_file_path,
                full_audio_path=full_audio_path,
                subtitle_ref=subtitle_ref,
                output_path=output_path,
                total_duration=total_duration,
            )
        else:
            # Fallback mode: solid color background
            _compose_fallback(
                full_audio_path=full_audio_path,
                subtitle_ref=subtitle_ref,
                output_path=output_path,
                total_duration=total_duration,
            )

        # Read output bytes and write via artifact store
        output_bytes = Path(output_path).read_bytes()
        ref = artifact_store.write_file(
            task_id=task_id,
            step_key="video_compose",
            artifact_type="final_video",
            filename="output.mp4",
            content=output_bytes,
        )

    except VideoComposeError:
        raise
    except Exception as exc:
        raise VideoComposeError(f"Video composition failed: {exc}") from exc
    finally:
        # Clean up temp files
        if concat_file_path and os.path.exists(concat_file_path):
            os.unlink(concat_file_path)
        if os.path.exists(output_path):
            os.unlink(output_path)

    return {
        "duration_seconds": total_duration,
        "resolution": "1280x720",
        "has_visual": not fallback_mode,
        "has_audio": True,
        "has_subtitles": True,
        "fallback_mode": fallback_mode,
        "storage_ref": ref.storage_ref,
    }
