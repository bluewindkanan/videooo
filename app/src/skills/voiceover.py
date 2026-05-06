"""Voiceover skill -- generate TTS audio from storyboard segments via edge-tts."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import edge_tts

from app.src.artifacts.store import ArtifactStore
from app.src.media.ffmpeg_utils import probe_duration, run_ffmpeg


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class VoiceoverError(Exception):
    """Raised when voiceover generation fails."""


# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_voiceover(
    *,
    storyboard_segments: list[dict[str, Any]],
    artifact_store: ArtifactStore,
    task_id: str,
) -> dict[str, Any]:
    """Generate voiceover audio from storyboard segments.

    For each segment, uses edge-tts to synthesize voiceover_text into audio.
    Captures WordBoundary events for subtitle timing. Writes per-segment MP3
    files and a concatenated full voiceover MP3.

    Parameters
    ----------
    storyboard_segments:
        List of storyboard segment dicts, each containing ``voiceover_text``.
    artifact_store:
        ArtifactStore for writing audio files.
    task_id:
        Task identifier for artifact organization.

    Returns
    -------
    dict
        Timing data with per-segment audio refs, durations, word boundaries,
        total duration, and full audio ref.

    Raises
    ------
    VoiceoverError
        If segments list is empty or TTS generation fails.
    """
    if not storyboard_segments:
        raise VoiceoverError("storyboard_segments must not be empty")

    voice = os.environ.get("VIDEOOO_TTS_VOICE", _DEFAULT_VOICE)

    segment_results: list[dict[str, Any]] = []
    seg_audio_paths: list[str] = []

    for seg in storyboard_segments:
        seg_index = seg["segment_index"]
        voiceover_text = seg.get("voiceover_text", "")
        if not voiceover_text:
            raise VoiceoverError(
                f"Segment {seg_index} has empty voiceover_text"
            )

        audio_bytes, word_boundaries = _synthesize_segment(
            text=voiceover_text,
            voice=voice,
        )

        ref = artifact_store.write_file(
            task_id=task_id,
            step_key="voiceover",
            artifact_type="audio",
            filename=f"seg_{seg_index}.mp3",
            content=audio_bytes,
        )

        duration = probe_duration(ref.storage_ref)

        segment_results.append({
            "segment_index": seg_index,
            "voiceover_text": voiceover_text,
            "segment_audio_ref": ref.storage_ref,
            "duration_seconds": duration,
            "word_boundaries": word_boundaries,
        })
        seg_audio_paths.append(ref.storage_ref)

    # Concatenate all segment audios into a single file
    full_audio_ref = _concat_segments(
        seg_audio_paths=seg_audio_paths,
        artifact_store=artifact_store,
        task_id=task_id,
    )

    total_duration = sum(s["duration_seconds"] for s in segment_results)

    return {
        "segments": segment_results,
        "total_duration_seconds": total_duration,
        "full_audio_ref": full_audio_ref.storage_ref,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _synthesize_segment(
    *,
    text: str,
    voice: str,
) -> tuple[bytes, list[dict[str, Any]]]:
    """Synthesize a single segment via edge-tts, returning audio bytes and word boundaries."""
    audio_chunks: list[bytes] = []
    word_boundaries: list[dict[str, Any]] = []

    communicate = edge_tts.Communicate(text, voice)

    for chunk in communicate.stream_sync():
        if chunk["type"] == "audio":
            data = chunk.get("data")
            if data:
                audio_chunks.append(data)
        elif chunk["type"] == "WordBoundary":
            word_boundaries.append({
                "text": chunk.get("text", ""),
                "offset_ms": int(chunk.get("offset", 0)),
                "duration_ms": int(chunk.get("duration", 0)),
            })

    if not audio_chunks:
        raise VoiceoverError(f"No audio received for text: {text[:50]}")

    return b"".join(audio_chunks), word_boundaries


def _concat_segments(
    *,
    seg_audio_paths: list[str],
    artifact_store: ArtifactStore,
    task_id: str,
) -> Any:
    """Concatenate segment MP3 files into a single full voiceover MP3 via FFmpeg concat demuxer."""
    # Write concat list to a temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for path in seg_audio_paths:
            f.write(f"file '{path}'\n")
        concat_list_path = f.name

    try:
        # Output to a temp file, then write through artifact_store
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as out_f:
            output_path = out_f.name

        run_ffmpeg([
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            output_path,
        ])

        audio_content = Path(output_path).read_bytes()

        ref = artifact_store.write_file(
            task_id=task_id,
            step_key="voiceover",
            artifact_type="audio",
            filename="full_voiceover.mp3",
            content=audio_content,
        )
        return ref
    finally:
        # Cleanup temp files
        try:
            Path(concat_list_path).unlink(missing_ok=True)
        except OSError:
            pass
        try:
            Path(output_path).unlink(missing_ok=True)  # type: ignore[possibly-undefined]
        except (OSError, NameError):
            pass
