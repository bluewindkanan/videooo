"""Review Script Skill — reviews script draft and storyboard quality via LLM."""
from __future__ import annotations

import json
from typing import List

from app.src.skills.llm_adapter import LLMAdapter, LLMParseError


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a senior short-video script editor and storyboard reviewer.

Given a script draft and a list of storyboard segments, identify quality issues.

Return a JSON array of finding objects. Each finding MUST have exactly these fields:
- "stage": "script" or "storyboard"
- "severity": "critical", "warning", or "info"
- "location_ref": a dot-path reference such as "script.hook", "script.body", \
"storyboard[0].visual_intent", "storyboard[1].voiceover_text", etc.
- "message": a concise description of the issue
- "suggested_fix": a concrete fix suggestion, or an empty string if none

If the script and storyboard have no issues, return an empty array [].

IMPORTANT: Return ONLY the JSON array. No markdown fences, no commentary.\
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_review_script(
    *,
    script_draft: dict,
    storyboard_segments: List[dict],
    llm_adapter: LLMAdapter,
) -> List[dict]:
    """Review script and storyboard quality via LLM, returning structured findings.

    Args:
        script_draft: Dict with keys hook, body, call_to_action, etc.
        storyboard_segments: List of storyboard segment dicts.
        llm_adapter: LLMAdapter instance for calling the LLM.

    Returns:
        List of finding dicts. Empty list if no issues.

    Raises:
        LLMParseError: If the LLM response cannot be parsed as JSON.
        LLMError: If the LLM call itself fails.
    """
    user_prompt = _build_user_prompt(script_draft, storyboard_segments)

    raw_response = llm_adapter.chat(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    return _parse_findings(raw_response)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_user_prompt(script_draft: dict, storyboard_segments: List[dict]) -> str:
    """Build the user prompt containing both inputs."""
    parts: list[str] = []

    parts.append("## Script Draft")
    parts.append(json.dumps(script_draft, ensure_ascii=False, indent=2))

    parts.append("")
    parts.append("## Storyboard Segments")
    parts.append(json.dumps(storyboard_segments, ensure_ascii=False, indent=2))

    parts.append("")
    parts.append("Review the above script and storyboard for quality issues. Return the JSON array of findings.")

    return "\n".join(parts)


def _parse_findings(raw_response: str) -> List[dict]:
    """Parse the LLM response into a list of finding dicts.

    Raises:
        LLMParseError: If response is not valid JSON or not a list.
    """
    try:
        data = json.loads(raw_response)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMParseError(
            f"Review response is not valid JSON. "
            f"Raw response (first 200 chars): {raw_response[:200]!r}. "
            f"Error: {exc}"
        ) from exc

    if not isinstance(data, list):
        raise LLMParseError(
            f"Review response is not a JSON array. "
            f"Got type: {type(data).__name__}. "
            f"Raw response (first 200 chars): {raw_response[:200]!r}"
        )

    return data
