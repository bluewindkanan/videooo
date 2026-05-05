"""LLM calling adapter — isolates provider differences behind a single interface."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import NoReturn


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """Base for all LLM adapter errors."""

    error_category: str = "unknown"

    def __init__(self, message: str, *, error_category: str = "unknown") -> None:
        super().__init__(message)
        self.error_category = error_category


class LLMRateLimitError(LLMError):
    """HTTP 429 — too many requests."""

    error_category = "rate_limit"

    def __init__(self, message: str = "Rate limited") -> None:
        super().__init__(message, error_category="rate_limit")


class LLMApiError(LLMError):
    """HTTP 5xx or network-level failure."""

    error_category = "api_error"

    def __init__(self, message: str = "API error") -> None:
        super().__init__(message, error_category="api_error")


class LLMContentFilterError(LLMError):
    """Content safety block — non-retryable."""

    error_category = "content_filter"

    def __init__(self, message: str = "Content filtered") -> None:
        super().__init__(message, error_category="content_filter")
        self.non_retryable: bool = True


class LLMParseError(LLMError):
    """Malformed response that could not be parsed."""

    error_category = "parse_error"

    def __init__(self, message: str = "Failed to parse response") -> None:
        super().__init__(message, error_category="parse_error")


# ---------------------------------------------------------------------------
# Defaults (DashScope / Tongyi Qianwen)
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_DEFAULT_MODEL = "qwen-plus"


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class LLMAdapter:
    """LLM calling adapter, isolating provider differences.

    Uses OpenAI-compatible ``/v1/chat/completions`` endpoint via
    ``urllib.request`` (stdlib only — no third-party HTTP clients).
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    # -- factory from environment variables ----------------------------------

    @classmethod
    def from_env(cls) -> LLMAdapter:
        """Create an adapter from environment variables.

        Uses ``LLM_BASE_URL``, ``LLM_API_KEY``, ``LLM_MODEL`` with
        DashScope defaults for base URL and model.
        """
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", _DEFAULT_BASE_URL),
            api_key=os.environ.get("LLM_API_KEY", ""),
            model=os.environ.get("LLM_MODEL", _DEFAULT_MODEL),
        )

    # -- chat ---------------------------------------------------------------

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request and return the assistant text.

        Returns the raw content string; the caller is responsible for
        any JSON parsing of the content itself.
        """
        url = f"{self.base_url}/chat/completions"
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        body = self._execute_request(req)
        return self._extract_content(body)

    # -- internal -----------------------------------------------------------

    def _execute_request(self, req: urllib.request.Request) -> bytes:
        """Execute the HTTP request, translating errors to domain exceptions."""
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise LLMRateLimitError(
                    f"Rate limited (HTTP 429)"
                ) from exc
            if exc.code >= 500:
                raise LLMApiError(
                    f"Server error (HTTP {exc.code})"
                ) from exc
            # Other HTTP errors (4xx except 429) treated as generic API errors
            raise LLMApiError(
                f"HTTP error {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMApiError(
                f"Network error: {exc.reason}"
            ) from exc

    def _extract_content(self, body: bytes) -> str:
        """Parse the JSON response body and return the assistant message text."""
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMParseError(
                f"Response is not valid JSON: {exc}"
            ) from exc

        try:
            choices = data["choices"]
            first = choices[0]
            finish_reason = first.get("finish_reason")
            message = first["message"]
            content: str = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMParseError(
                f"Unexpected response structure: {exc}"
            ) from exc

        if finish_reason == "content_filter":
            raise LLMContentFilterError("Content blocked by safety filter")

        return content
