"""Script generation skill — produces a short video script draft via LLM."""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from app.src.skills.llm_adapter import LLMParseError

if TYPE_CHECKING:
    from app.src.skills.llm_adapter import LLMAdapter


_SYSTEM_PROMPT = """\
You are an expert short-video scriptwriter. Given a topic, draft, or article URL, \
produce a short video script as a JSON object with exactly these fields:

- "hook": string — an attention-grabbing opening line (1-2 sentences)
- "body": string — the main content (2-4 paragraphs)
- "call_to_action": string — a closing line encouraging viewer action
- "estimated_duration_seconds": integer — estimated spoken duration in seconds (15-120)

Respond with ONLY the JSON object, no markdown fences or extra text.\
"""

_USER_PROMPT_TEMPLATES: dict[str, str] = {
    "topic": "Write a short video script about the following topic:\n\n{input}",
    "draft": "Turn this rough draft into a polished short video script:\n\n{input}",
    "article_url": "Write a short video script summarizing the key points from this article:\n\n{input}",
}

_REQUIRED_FIELDS = ("hook", "body", "call_to_action", "estimated_duration_seconds")


def run_script_generation(
    *,
    input_kind: str,
    input_text: str,
    llm_adapter: LLMAdapter,
) -> dict:
    """Generate a short video script draft via LLM.

    Parameters
    ----------
    input_kind:
        One of "topic", "draft", "article_url".
    input_text:
        The raw input content.
    llm_adapter:
        An LLMAdapter instance used to call the LLM.

    Returns
    -------
    dict with keys: hook, body, call_to_action, estimated_duration_seconds.

    Raises
    ------
    LLMParseError
        If the LLM response cannot be parsed as valid JSON matching the schema.
    LLMError
        Propagated from the LLM adapter on API / rate-limit / content-filter errors.
    """
    template = _USER_PROMPT_TEMPLATES.get(input_kind, _USER_PROMPT_TEMPLATES["topic"])
    user_prompt = template.format(input=input_text)

    raw_text = llm_adapter.chat(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    return _parse_script_response(raw_text)


def _parse_script_response(raw_text: str) -> dict:
    """Parse the raw LLM text into a validated script dict.

    Raises LLMParseError with the raw response attached if parsing fails.
    """
    try:
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_text.strip()).rstrip('`').strip()
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMParseError(
            f"Script generation produced invalid JSON. Raw response: {raw_text}"
        ) from exc

    if not isinstance(data, dict):
        raise LLMParseError(
            f"Script generation returned non-object JSON. Raw response: {raw_text}"
        )

    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if missing:
        raise LLMParseError(
            f"Script response missing required fields: {missing}. Raw response: {raw_text}"
        )

    if not isinstance(data["estimated_duration_seconds"], int):
        raise LLMParseError(
            f"estimated_duration_seconds must be int, got {type(data['estimated_duration_seconds']).__name__}. "
            f"Raw response: {raw_text}"
        )

    return {
        "hook": str(data["hook"]),
        "body": str(data["body"]),
        "call_to_action": str(data["call_to_action"]),
        "estimated_duration_seconds": data["estimated_duration_seconds"],
    }
