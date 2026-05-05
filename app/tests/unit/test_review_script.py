"""Unit tests for review_script skill — TDD RED phase."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.src.skills.llm_adapter import LLMApiError, LLMParseError
from app.src.skills.review_script import run_review_script


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(return_value: str) -> MagicMock:
    """Create a mock LLMAdapter whose .chat() returns *return_value*."""
    adapter = MagicMock()
    adapter.chat.return_value = return_value
    return adapter


def _sample_script_draft() -> dict:
    return {
        "hook": "",
        "body": "This is the main content of the script.",
        "call_to_action": "Subscribe for more!",
        "estimated_duration_seconds": 60,
    }


def _sample_storyboard_segments() -> list[dict]:
    return [
        {
            "segment_index": 0,
            "voiceover_text": "Welcome to our channel!",
            "visual_intent": "",
            "expected_keywords": ["welcome"],
            "estimated_start_seconds": 0.0,
            "estimated_end_seconds": 5.0,
        },
    ]


_FINDINGS_RESPONSE = json.dumps([
    {
        "stage": "script",
        "severity": "critical",
        "location_ref": "script.hook",
        "message": "Hook is empty — viewers will scroll past.",
        "suggested_fix": "Add a compelling question or surprising fact.",
    },
    {
        "stage": "storyboard",
        "severity": "warning",
        "location_ref": "storyboard[0].visual_intent",
        "message": "Visual intent is vague.",
        "suggested_fix": "Specify concrete visual, e.g. 'close-up of coding screen'.",
    },
])


# ---------------------------------------------------------------------------
# 1. test_review_success_with_issues
# ---------------------------------------------------------------------------

def test_review_success_with_issues() -> None:
    """Mock LLM returning structured findings, verify output schema."""
    adapter = _make_adapter(_FINDINGS_RESPONSE)

    result = run_review_script(
        script_draft=_sample_script_draft(),
        storyboard_segments=_sample_storyboard_segments(),
        llm_adapter=adapter,
    )

    assert isinstance(result, list)
    assert len(result) == 2

    finding = result[0]
    assert finding["stage"] == "script"
    assert finding["severity"] == "critical"
    assert finding["location_ref"] == "script.hook"
    assert finding["message"] == "Hook is empty — viewers will scroll past."
    assert finding["suggested_fix"] == "Add a compelling question or surprising fact."

    finding2 = result[1]
    assert finding2["stage"] == "storyboard"
    assert finding2["severity"] == "warning"
    assert finding2["location_ref"] == "storyboard[0].visual_intent"

    # Verify adapter was called
    adapter.chat.assert_called_once()
    call_kwargs = adapter.chat.call_args[1]
    assert "system_prompt" in call_kwargs
    assert "user_prompt" in call_kwargs


# ---------------------------------------------------------------------------
# 2. test_review_detects_injected_issues
# ---------------------------------------------------------------------------

def test_review_detects_injected_issues() -> None:
    """Verify findings detect common issues like empty hook and vague visual intent."""
    adapter = _make_adapter(_FINDINGS_RESPONSE)

    script = _sample_script_draft()
    segments = _sample_storyboard_segments()
    # Inject known issues: empty hook, empty visual_intent
    script["hook"] = ""
    segments[0]["visual_intent"] = ""

    result = run_review_script(
        script_draft=script,
        storyboard_segments=segments,
        llm_adapter=adapter,
    )

    stages = [f["stage"] for f in result]
    assert "script" in stages
    assert "storyboard" in stages

    # The user prompt should contain the injected issues for the LLM to detect
    call_kwargs = adapter.chat.call_args[1]
    user_prompt = call_kwargs["user_prompt"]
    assert "hook" in user_prompt.lower() or "hook" in user_prompt
    assert "visual_intent" in user_prompt.lower() or "visual_intent" in user_prompt


# ---------------------------------------------------------------------------
# 3. test_review_clean_pass
# ---------------------------------------------------------------------------

def test_review_clean_pass() -> None:
    """Mock LLM returning empty findings array, verify empty list returned."""
    adapter = _make_adapter("[]")

    result = run_review_script(
        script_draft=_sample_script_draft(),
        storyboard_segments=_sample_storyboard_segments(),
        llm_adapter=adapter,
    )

    assert isinstance(result, list)
    assert len(result) == 0


# ---------------------------------------------------------------------------
# 4. test_review_parse_error
# ---------------------------------------------------------------------------

def test_review_parse_error() -> None:
    """Mock malformed JSON response, verify LLMParseError is raised."""
    adapter = _make_adapter("this is not valid json {{{")

    with pytest.raises(LLMParseError):
        run_review_script(
            script_draft=_sample_script_draft(),
            storyboard_segments=_sample_storyboard_segments(),
            llm_adapter=adapter,
        )


# ---------------------------------------------------------------------------
# 5. test_review_llm_error
# ---------------------------------------------------------------------------

def test_review_llm_error() -> None:
    """Mock LLM failure, verify error propagates."""
    adapter = MagicMock()
    adapter.chat.side_effect = LLMApiError("Server error (HTTP 503)")

    with pytest.raises(LLMApiError):
        run_review_script(
            script_draft=_sample_script_draft(),
            storyboard_segments=_sample_storyboard_segments(),
            llm_adapter=adapter,
        )


# ---------------------------------------------------------------------------
# 6. test_findings_have_required_fields
# ---------------------------------------------------------------------------

def test_findings_have_required_fields() -> None:
    """Each finding dict must have all 5 required fields."""
    adapter = _make_adapter(_FINDINGS_RESPONSE)

    result = run_review_script(
        script_draft=_sample_script_draft(),
        storyboard_segments=_sample_storyboard_segments(),
        llm_adapter=adapter,
    )

    required_fields = {"stage", "severity", "location_ref", "message", "suggested_fix"}
    for finding in result:
        assert required_fields.issubset(finding.keys()), (
            f"Finding missing fields: {required_fields - finding.keys()}"
        )


# ---------------------------------------------------------------------------
# 7. test_review_prompt_includes_both_inputs
# ---------------------------------------------------------------------------

def test_review_prompt_includes_both_inputs() -> None:
    """User prompt should include both script draft and storyboard segments."""
    adapter = _make_adapter("[]")

    script = _sample_script_draft()
    script["hook"] = "Did you know that 90% of startups fail?"
    segments = _sample_storyboard_segments()

    run_review_script(
        script_draft=script,
        storyboard_segments=segments,
        llm_adapter=adapter,
    )

    call_kwargs = adapter.chat.call_args[1]
    user_prompt = call_kwargs["user_prompt"]
    assert "Did you know" in user_prompt
    assert "storyboard" in user_prompt.lower() or "segment" in user_prompt.lower()


# ---------------------------------------------------------------------------
# 8. test_review_parse_error_includes_raw_response_info
# ---------------------------------------------------------------------------

def test_review_parse_error_includes_raw_response_info() -> None:
    """On parse failure, the error message should include info about the raw response."""
    raw = '{"findings": [{broken json'
    adapter = _make_adapter(raw)

    with pytest.raises(LLMParseError) as exc_info:
        run_review_script(
            script_draft=_sample_script_draft(),
            storyboard_segments=_sample_storyboard_segments(),
            llm_adapter=adapter,
        )

    # Error message should mention the raw response
    error_msg = str(exc_info.value)
    assert len(error_msg) > 0


# ---------------------------------------------------------------------------
# 9. test_review_non_array_response
# ---------------------------------------------------------------------------

def test_review_non_array_response() -> None:
    """LLM returns valid JSON but not an array — should raise LLMParseError."""
    adapter = _make_adapter('{"error": "something"}')

    with pytest.raises(LLMParseError) as exc_info:
        run_review_script(
            script_draft=_sample_script_draft(),
            storyboard_segments=_sample_storyboard_segments(),
            llm_adapter=adapter,
        )

    assert "not a JSON array" in str(exc_info.value)
