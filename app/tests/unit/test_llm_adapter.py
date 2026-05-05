"""Unit tests for LLMAdapter — TDD RED phase."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from app.src.skills.llm_adapter import (
    LLMAdapter,
    LLMApiError,
    LLMContentFilterError,
    LLMParseError,
    LLMRateLimitError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(**overrides: str) -> LLMAdapter:
    defaults = dict(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="test-key-123",
        model="qwen-plus",
    )
    defaults.update(overrides)
    return LLMAdapter(**defaults)


def _mock_response(body: bytes, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# 1. test_chat_success
# ---------------------------------------------------------------------------

def test_chat_success() -> None:
    """Mock HTTP 200, verify request format and response text extraction."""
    adapter = _make_adapter()
    response_body = json.dumps({
        "choices": [
            {"message": {"content": "Hello, world!"}}
        ]
    }).encode()

    mock_resp = _mock_response(response_body, status=200)

    with patch.object(urllib.request, "urlopen", return_value=mock_resp) as mock_urlopen:
        result = adapter.chat(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello.",
            max_tokens=512,
        )

    assert result == "Hello, world!"

    # Verify the request was constructed correctly
    mock_urlopen.assert_called_once()
    req: urllib.request.Request = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert req.get_header("Content-type") == "application/json"
    assert req.get_header("Authorization") == "Bearer test-key-123"

    sent = json.loads(req.data)
    assert sent["model"] == "qwen-plus"
    assert sent["messages"] == [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello."},
    ]
    assert sent["max_tokens"] == 512


# ---------------------------------------------------------------------------
# 2. test_chat_rate_limit
# ---------------------------------------------------------------------------

def test_chat_rate_limit() -> None:
    """Mock HTTP 429, verify raises LLMRateLimitError."""
    adapter = _make_adapter()

    with patch.object(
        urllib.request, "urlopen",
        side_effect=urllib.error.HTTPError(
            url="https://example.com", code=429,
            msg="Too Many Requests", hdrs=None, fp=None,
        ),
    ):
        with pytest.raises(LLMRateLimitError) as exc_info:
            adapter.chat(system_prompt="sys", user_prompt="usr")

    assert exc_info.value.error_category == "rate_limit"


# ---------------------------------------------------------------------------
# 3. test_chat_api_error
# ---------------------------------------------------------------------------

def test_chat_api_error() -> None:
    """Mock HTTP 500, verify raises LLMApiError."""
    adapter = _make_adapter()

    with patch.object(
        urllib.request, "urlopen",
        side_effect=urllib.error.HTTPError(
            url="https://example.com", code=500,
            msg="Internal Server Error", hdrs=None, fp=None,
        ),
    ):
        with pytest.raises(LLMApiError) as exc_info:
            adapter.chat(system_prompt="sys", user_prompt="usr")

    assert exc_info.value.error_category == "api_error"


# ---------------------------------------------------------------------------
# 4. test_chat_network_error
# ---------------------------------------------------------------------------

def test_chat_network_error() -> None:
    """Mock connection error (URLError), verify raises LLMApiError."""
    adapter = _make_adapter()

    with patch.object(
        urllib.request, "urlopen",
        side_effect=urllib.error.URLError(reason="Connection refused"),
    ):
        with pytest.raises(LLMApiError) as exc_info:
            adapter.chat(system_prompt="sys", user_prompt="usr")

    assert exc_info.value.error_category == "api_error"


# ---------------------------------------------------------------------------
# 5. test_chat_content_filter
# ---------------------------------------------------------------------------

def test_chat_content_filter() -> None:
    """Mock content safety block response, verify raises LLMContentFilterError."""
    adapter = _make_adapter()
    response_body = json.dumps({
        "choices": [
            {"message": {"content": ""}, "finish_reason": "content_filter"}
        ]
    }).encode()

    mock_resp = _mock_response(response_body, status=200)

    with patch.object(urllib.request, "urlopen", return_value=mock_resp):
        with pytest.raises(LLMContentFilterError) as exc_info:
            adapter.chat(system_prompt="sys", user_prompt="usr")

    assert exc_info.value.error_category == "content_filter"
    assert exc_info.value.non_retryable is True


# ---------------------------------------------------------------------------
# 6. test_from_env
# ---------------------------------------------------------------------------

def test_from_env() -> None:
    """Verify env var loading with defaults."""
    env = {
        "LLM_BASE_URL": "https://custom.api/v1",
        "LLM_API_KEY": "env-key-456",
        "LLM_MODEL": "custom-model",
    }
    with patch.dict(os.environ, env, clear=False):
        adapter = LLMAdapter.from_env()

    assert adapter.base_url == "https://custom.api/v1"
    assert adapter.api_key == "env-key-456"
    assert adapter.model == "custom-model"


def test_from_env_defaults() -> None:
    """Verify defaults when env vars are not set."""
    env_to_clear = ["LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"]
    with patch.dict(os.environ, {}, clear=True):
        # Remove any existing values
        for key in env_to_clear:
            os.environ.pop(key, None)
        adapter = LLMAdapter.from_env()

    assert adapter.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert adapter.model == "qwen-plus"


# ---------------------------------------------------------------------------
# 7. test_chat_parse_error
# ---------------------------------------------------------------------------

def test_chat_parse_error() -> None:
    """Mock malformed response body, verify raises LLMParseError."""
    adapter = _make_adapter()
    response_body = b"this is not json"

    mock_resp = _mock_response(response_body, status=200)

    with patch.object(urllib.request, "urlopen", return_value=mock_resp):
        with pytest.raises(LLMParseError) as exc_info:
            adapter.chat(system_prompt="sys", user_prompt="usr")

    assert exc_info.value.error_category == "parse_error"
