"""Material extract skill — cut source videos into fixed-duration clips via FFmpeg."""
from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from app.src.media import ffmpeg_utils

if TYPE_CHECKING:
    from app.src.artifacts.store import ArtifactStore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLIP_DURATION_SECONDS = 5.0

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MaterialExtractError(Exception):
    """Raised when material extraction fails due to missing FFmpeg or other errors."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_material_extract(
    *,
    source_video_refs: list[str],
    artifact_store: "ArtifactStore",
    task_id: str,
) -> dict:
    """Extract fixed-duration clips from source videos using FFmpeg.

    Parameters
    ----------
    source_video_refs:
        List of storage_ref paths to source video files.
    artifact_store:
        ArtifactStore for writing clip files.
    task_id:
        The task ID for artifact storage paths.

    Returns
    -------
    A clip_manifest dict with per-clip metadata.

    Raises
    ------
    MaterialExtractError
        If FFmpeg is not available.
    """
    if not source_video_refs:
        return {
            "clips": [],
            "total_clip_duration_seconds": 0.0,
        }

    # Check FFmpeg availability
    available, version_or_error = ffmpeg_utils.check_ffmpeg_available()
    if not available:
        raise MaterialExtractError(
            f"FFmpeg not available: {version_or_error}"
        )

    clips: list[dict] = []
    total_duration = 0.0

    for source_ref in source_video_refs:
        duration = ffmpeg_utils.probe_duration(source_ref)
        num_clips = math.ceil(duration / CLIP_DURATION_SECONDS)

        for clip_idx in range(num_clips):
            start = clip_idx * CLIP_DURATION_SECONDS
            end = min(start + CLIP_DURATION_SECONDS, duration)
            clip_dur = end - start

            # Extract clip via FFmpeg to a temp file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                ffmpeg_utils.run_ffmpeg([
                    "-i", source_ref,
                    "-ss", str(start),
                    "-to", str(end),
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    tmp_path,
                ])

                clip_bytes = Path(tmp_path).read_bytes()
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            ref = artifact_store.write_file(
                task_id=task_id,
                step_key="material_extract",
                artifact_type="clip",
                filename=f"clip_{clip_idx}.mp4",
                content=clip_bytes,
            )

            clips.append({
                "clip_index": clip_idx,
                "source_ref": source_ref,
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": clip_dur,
                "storage_ref": ref.storage_ref,
            })
            total_duration += clip_dur

    return {
        "clips": clips,
        "total_clip_duration_seconds": total_duration,
    }
