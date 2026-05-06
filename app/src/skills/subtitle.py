"""Subtitle skill -- generate SRT subtitles from voiceover timing data."""
from __future__ import annotations

from typing import Any

from app.src.artifacts.store import ArtifactStore


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

_LONG_SEGMENT_THRESHOLD_MS = 10_000


def ms_to_srt(ms: int) -> str:
    """Convert milliseconds to SRT timestamp format HH:MM:SS,mmm."""
    hours = ms // 3_600_000
    minutes = (ms % 3_600_000) // 60_000
    seconds = (ms % 60_000) // 1_000
    millis = ms % 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_srt_entries(
    *,
    segments: list[dict[str, Any]],
) -> list[tuple[int, int, str]]:
    """Build a list of (start_ms, end_ms, text) tuples from voiceover segments.

    Long segments (>10s) are split at the word boundary closest to the midpoint.
    """
    entries: list[tuple[int, int, str]] = []
    global_offset_ms = 0

    for seg in segments:
        voiceover_text: str = seg.get("voiceover_text", "")
        duration_seconds: float = seg.get("duration_seconds", 0.0)
        duration_ms = int(duration_seconds * 1_000)
        word_boundaries: list[dict[str, Any]] = seg.get("word_boundaries", [])

        if not word_boundaries:
            # Fallback: use segment-level timing
            start_ms = global_offset_ms
            end_ms = global_offset_ms + duration_ms
            entries.append((start_ms, end_ms, voiceover_text))
        elif duration_ms > _LONG_SEGMENT_THRESHOLD_MS:
            # Split at midpoint word boundary
            midpoint_ms = duration_ms // 2
            # Find the word boundary closest to the midpoint
            split_idx = 0
            best_diff = abs(word_boundaries[0]["offset_ms"] - midpoint_ms)
            for i, wb in enumerate(word_boundaries):
                diff = abs(wb["offset_ms"] - midpoint_ms)
                if diff < best_diff:
                    best_diff = diff
                    split_idx = i

            # First half: start -> split word end
            first_start = global_offset_ms + word_boundaries[0]["offset_ms"]
            split_wb = word_boundaries[split_idx]
            first_end = global_offset_ms + split_wb["offset_ms"] + split_wb["duration_ms"]
            entries.append((first_start, first_end, voiceover_text))

            # Second half: next word start -> last word end
            if split_idx + 1 < len(word_boundaries):
                second_start = global_offset_ms + word_boundaries[split_idx + 1]["offset_ms"]
            else:
                second_start = first_end
            last_wb = word_boundaries[-1]
            second_end = global_offset_ms + last_wb["offset_ms"] + last_wb["duration_ms"]
            entries.append((second_start, second_end, voiceover_text))
        else:
            # Normal segment: one entry
            first_wb = word_boundaries[0]
            last_wb = word_boundaries[-1]
            start_ms = global_offset_ms + first_wb["offset_ms"]
            end_ms = global_offset_ms + last_wb["offset_ms"] + last_wb["duration_ms"]
            entries.append((start_ms, end_ms, voiceover_text))

        global_offset_ms += duration_ms

    return entries


def _format_srt(entries: list[tuple[int, int, str]]) -> str:
    """Format SRT entries into the standard SRT file content."""
    if not entries:
        return ""

    blocks: list[str] = []
    for idx, (start_ms, end_ms, text) in enumerate(entries, start=1):
        start_ts = ms_to_srt(start_ms)
        end_ts = ms_to_srt(end_ms)
        blocks.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}")

    return "\n\n".join(blocks) + "\n"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_subtitle(
    *,
    voiceover_timing: dict[str, Any],
    artifact_store: ArtifactStore,
    task_id: str,
) -> dict[str, Any]:
    """Generate SRT subtitles from voiceover timing data.

    Parameters
    ----------
    voiceover_timing:
        Timing data produced by the voiceover skill, containing per-segment
        durations and word_boundaries.
    artifact_store:
        ArtifactStore for writing the .srt file.
    task_id:
        Task identifier for artifact organization.

    Returns
    -------
    dict
        Metadata about the generated subtitle including entry count,
        total duration, source type, and the srt file reference.
    """
    segments: list[dict[str, Any]] = voiceover_timing.get("segments", [])
    total_duration = voiceover_timing.get("total_duration_seconds", 0.0)

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
        "total_duration_seconds": total_duration,
        "source": "edge_tts_timing",
        "srt_ref": ref.storage_ref,
    }
