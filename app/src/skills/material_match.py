"""Material match skill — duration-based assignment of clips to voiceover segments."""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_material_match(
    *,
    voiceover_timing: dict[str, Any],
    clip_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Assign clips to voiceover segments based on sequential duration coverage.

    Parameters
    ----------
    voiceover_timing:
        Output from the voiceover skill containing ``segments`` with
        ``segment_index`` and ``duration_seconds``.
    clip_manifest:
        Output from the material_extract skill containing ``clips`` with
        ``clip_index``, ``start_seconds``, ``end_seconds``, and
        ``duration_seconds``.

    Returns
    -------
    dict
        ``matches`` list of per-segment assignments and ``fallback_mode`` flag.
    """
    segments = voiceover_timing.get("segments", [])
    clips = clip_manifest.get("clips", [])

    # Edge case: no segments -> empty matches
    if not segments:
        return {"matches": [], "fallback_mode": False}

    # Edge case: no clips -> fallback mode with empty assignments
    if not clips:
        return {
            "matches": [
                {
                    "segment_index": seg["segment_index"],
                    "voiceover_duration": seg["duration_seconds"],
                    "assigned_clips": [],
                }
                for seg in sorted(segments, key=lambda s: s["segment_index"])
            ],
            "fallback_mode": True,
        }

    # Build flat clip pool with durations
    clip_pool = [
        {
            "clip_index": c["clip_index"],
            "start_seconds": c["start_seconds"],
            "end_seconds": c["end_seconds"],
            "duration_seconds": c["duration_seconds"],
        }
        for c in sorted(clips, key=lambda c: c["clip_index"])
    ]
    num_clips = len(clip_pool)

    matches: list[dict[str, Any]] = []

    # Track cursor position across the clip pool
    current_clip_pos = 0          # index into clip_pool
    remaining_in_clip = clip_pool[0]["duration_seconds"]  # remaining time in current clip

    for seg in sorted(segments, key=lambda s: s["segment_index"]):
        seg_duration = seg["duration_seconds"]
        assigned: list[dict[str, Any]] = []
        remaining_seg = seg_duration

        while remaining_seg > 0:
            clip = clip_pool[current_clip_pos]

            if remaining_in_clip <= 0:
                # Move to next clip (with modulo looping)
                current_clip_pos = (current_clip_pos + 1) % num_clips
                remaining_in_clip = clip_pool[current_clip_pos]["duration_seconds"]
                continue

            used = min(remaining_in_clip, remaining_seg)
            clip_start = clip["end_seconds"] - remaining_in_clip
            clip_end = clip_start + used

            assigned.append({
                "clip_index": clip["clip_index"],
                "start_seconds": clip_start,
                "end_seconds": clip_end,
                "duration_used": used,
            })

            remaining_in_clip -= used
            remaining_seg -= used

            if remaining_in_clip <= 0:
                current_clip_pos = (current_clip_pos + 1) % num_clips
                remaining_in_clip = clip_pool[current_clip_pos]["duration_seconds"]

        matches.append({
            "segment_index": seg["segment_index"],
            "voiceover_duration": seg_duration,
            "assigned_clips": assigned,
        })

    return {"matches": matches, "fallback_mode": False}
