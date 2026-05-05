"""Storyboard skill — generates visual segments from a script draft via LLM."""
from __future__ import annotations

import json
import re
from typing import Any

from app.src.skills.llm_adapter import LLMAdapter, LLMParseError

# ---------------------------------------------------------------------------
# Storyboard segment field names (authoritative)
# ---------------------------------------------------------------------------

_REQUIRED_SEGMENT_FIELDS = frozenset({
    "segment_index",
    "voiceover_text",
    "visual_intent",
    "expected_keywords",
    "estimated_start_seconds",
    "estimated_end_seconds",
})

_SYSTEM_PROMPT = (
    "You are a video storyboard planner. "
    "Given a script draft, produce a JSON array of storyboard segments. "
    "Each segment must be an object with exactly these fields: "
    "segment_index (int), voiceover_text (str), visual_intent (str), "
    "expected_keywords (list of str), estimated_start_seconds (float), "
    "estimated_end_seconds (float). "
    "Return ONLY the JSON array — no markdown fences, no commentary."
)


def run_storyboard(
    *,
    script_draft: dict[str, Any],
    llm_adapter: LLMAdapter,
) -> list[dict[str, Any]]:
    """Generate storyboard segments from a script draft via LLM.

    Parameters
    ----------
    script_draft:
        Dict with keys: hook, body, call_to_action, estimated_duration_seconds.
    llm_adapter:
        An LLMAdapter instance used to call the language model.

    Returns
    -------
    list[dict]
        A list of storyboard segment dicts, each containing the six
        required fields.

    Raises
    ------
    LLMParseError
        If the LLM response cannot be parsed as a JSON array of valid segments.
    LLMError
        Propagated from the adapter on API / rate-limit / content-filter failures.
    """
    user_prompt = _build_user_prompt(script_draft)

    raw_response = llm_adapter.chat(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    segments = _parse_segments(raw_response)
    _validate_segments(segments)
    return segments


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_user_prompt(script_draft: dict[str, Any]) -> str:
    """Format the script draft into a user prompt for the LLM."""
    parts = [
        f"Hook: {script_draft['hook']}",
        f"Body: {script_draft['body']}",
        f"Call to Action: {script_draft['call_to_action']}",
        f"Estimated Duration (seconds): {script_draft['estimated_duration_seconds']}",
    ]
    return "\n".join(parts)


def _parse_segments(raw_response: str) -> list[dict[str, Any]]:
    """Parse the raw LLM response into a list of segment dicts."""
    try:
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_response.strip()).rstrip('`').strip()
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMParseError(
            f"Storyboard response is not valid JSON: {exc}. "
            f"Raw response (first 200 chars): {raw_response[:200]}"
        ) from exc

    if not isinstance(data, list):
        raise LLMParseError(
            f"Storyboard response is not a JSON array. "
            f"Got type: {type(data).__name__}. "
            f"Raw response (first 200 chars): {raw_response[:200]}"
        )

    return data


def _validate_segments(segments: list[dict[str, Any]]) -> None:
    """Ensure every segment dict has all required fields with correct types."""
    for i, segment in enumerate(segments):
        missing = _REQUIRED_SEGMENT_FIELDS - segment.keys()
        if missing:
            raise LLMParseError(
                f"Segment {i} is missing required fields: {sorted(missing)}. "
                f"Segment data: {json.dumps(segment, ensure_ascii=False)[:200]}"
            )
