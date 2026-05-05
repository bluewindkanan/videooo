"""Unit tests for the storyboard skill — TDD RED phase."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.src.skills.llm_adapter import LLMApiError, LLMParseError
from app.src.skills.storyboard import run_storyboard

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_SCRIPT_DRAFT: dict[str, Any] = {
    "hook": "你知道吗？这个技巧可以帮你节省50%的时间",
    "body": "首先打开设置页面，然后找到高级选项，最后点击一键优化按钮",
    "call_to_action": "关注我，获取更多实用技巧",
    "estimated_duration_seconds": 30,
}

VALID_SEGMENTS: list[dict[str, Any]] = [
    {
        "segment_index": 0,
        "voiceover_text": "你知道吗？这个技巧可以帮你节省50%的时间",
        "visual_intent": "展示效率对比图表",
        "expected_keywords": ["节省", "时间", "技巧"],
        "estimated_start_seconds": 0.0,
        "estimated_end_seconds": 5.0,
    },
    {
        "segment_index": 1,
        "voiceover_text": "首先打开设置页面，然后找到高级选项，最后点击一键优化按钮",
        "visual_intent": "屏幕录制展示操作步骤",
        "expected_keywords": ["设置", "高级", "优化"],
        "estimated_start_seconds": 5.0,
        "estimated_end_seconds": 20.0,
    },
    {
        "segment_index": 2,
        "voiceover_text": "关注我，获取更多实用技巧",
        "visual_intent": "频道logo与订阅按钮",
        "expected_keywords": ["关注", "技巧"],
        "estimated_start_seconds": 20.0,
        "estimated_end_seconds": 25.0,
    },
]


def _make_llm_adapter(response: str) -> MagicMock:
    """Create a mock LLMAdapter that returns the given response string."""
    adapter = MagicMock()
    adapter.chat.return_value = response
    return adapter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_generate_storyboard_success() -> None:
    """Mock LLM returning valid JSON array — verify segments returned."""
    adapter = _make_llm_adapter(json.dumps(VALID_SEGMENTS))

    result = run_storyboard(script_draft=SAMPLE_SCRIPT_DRAFT, llm_adapter=adapter)

    assert isinstance(result, list)
    assert len(result) == 3


def test_segments_have_required_fields() -> None:
    """Each segment must contain all 6 required fields."""
    adapter = _make_llm_adapter(json.dumps(VALID_SEGMENTS))

    result = run_storyboard(script_draft=SAMPLE_SCRIPT_DRAFT, llm_adapter=adapter)

    required_fields = {
        "segment_index",
        "voiceover_text",
        "visual_intent",
        "expected_keywords",
        "estimated_start_seconds",
        "estimated_end_seconds",
    }
    for segment in result:
        assert required_fields.issubset(segment.keys()), (
            f"Missing fields: {required_fields - segment.keys()}"
        )


def test_segments_correspond_to_script() -> None:
    """Verify the LLM prompt includes the script draft content."""
    adapter = _make_llm_adapter(json.dumps(VALID_SEGMENTS))

    run_storyboard(script_draft=SAMPLE_SCRIPT_DRAFT, llm_adapter=adapter)

    adapter.chat.assert_called_once()
    call_kwargs = adapter.chat.call_args.kwargs
    user_prompt = call_kwargs["user_prompt"]

    # Script content must appear in the prompt sent to the LLM
    assert SAMPLE_SCRIPT_DRAFT["hook"] in user_prompt
    assert SAMPLE_SCRIPT_DRAFT["body"] in user_prompt
    assert SAMPLE_SCRIPT_DRAFT["call_to_action"] in user_prompt
    assert str(SAMPLE_SCRIPT_DRAFT["estimated_duration_seconds"]) in user_prompt


def test_generate_storyboard_parse_error() -> None:
    """Malformed JSON from LLM should raise LLMParseError."""
    adapter = _make_llm_adapter("this is not json {{{")

    with pytest.raises(LLMParseError):
        run_storyboard(script_draft=SAMPLE_SCRIPT_DRAFT, llm_adapter=adapter)


def test_generate_storyboard_llm_error() -> None:
    """LLM failure should propagate as-is."""
    adapter = MagicMock()
    adapter.chat.side_effect = LLMApiError("Server error (HTTP 500)")

    with pytest.raises(LLMApiError):
        run_storyboard(script_draft=SAMPLE_SCRIPT_DRAFT, llm_adapter=adapter)
