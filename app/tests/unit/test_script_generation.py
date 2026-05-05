"""Unit tests for script_generation skill and StepRunner dispatch."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import StepStatus
from app.src.skills.llm_adapter import LLMApiError, LLMParseError
from app.src.storage.sqlite import SqliteStore
from app.src.workers.step_runner import StepRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm_adapter(response_text: str) -> MagicMock:
    """Create a mock LLMAdapter whose .chat() returns *response_text*."""
    adapter = MagicMock()
    adapter.chat.return_value = response_text
    return adapter


def _valid_script_json() -> str:
    return json.dumps(
        {
            "hook": "Did you know that sleep boosts memory?",
            "body": "Recent studies show that 7-9 hours of sleep consolidates learning.",
            "call_to_action": "Follow for more brain hacks!",
            "estimated_duration_seconds": 30,
        },
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Pure skill tests
# ---------------------------------------------------------------------------

class TestRunScriptGeneration:
    """Tests for the run_script_generation pure skill function."""

    def test_generate_script_topic_input(self) -> None:
        """Mock LLM returning valid JSON, verify schema with topic input."""
        from app.src.skills.script_generation import run_script_generation

        adapter = _make_llm_adapter(_valid_script_json())

        result = run_script_generation(
            input_kind="topic",
            input_text="How sleep improves memory",
            llm_adapter=adapter,
        )

        assert isinstance(result, dict)
        assert "hook" in result
        assert "body" in result
        assert "call_to_action" in result
        assert "estimated_duration_seconds" in result
        assert isinstance(result["estimated_duration_seconds"], int)
        # Verify adapter was called with correct prompts
        adapter.chat.assert_called_once()
        call_kwargs = adapter.chat.call_args[1]
        assert "scriptwriter" in call_kwargs["system_prompt"].lower()
        assert "sleep" in call_kwargs["user_prompt"]

    def test_generate_script_draft_input(self) -> None:
        """Verify draft input is handled correctly."""
        from app.src.skills.script_generation import run_script_generation

        adapter = _make_llm_adapter(_valid_script_json())

        result = run_script_generation(
            input_kind="draft",
            input_text="I want to talk about productivity tips for remote workers",
            llm_adapter=adapter,
        )

        assert isinstance(result, dict)
        assert "hook" in result
        assert "body" in result
        assert "call_to_action" in result
        assert "estimated_duration_seconds" in result
        # Verify the draft text appears in the user prompt
        call_kwargs = adapter.chat.call_args[1]
        assert "productivity" in call_kwargs["user_prompt"]

    def test_generate_script_article_url_input(self) -> None:
        """Verify article_url input kind is handled."""
        from app.src.skills.script_generation import run_script_generation

        adapter = _make_llm_adapter(_valid_script_json())

        result = run_script_generation(
            input_kind="article_url",
            input_text="https://example.com/article-about-ai",
            llm_adapter=adapter,
        )

        assert isinstance(result, dict)
        assert "hook" in result

    def test_generate_script_parse_error(self) -> None:
        """Mock malformed LLM response, verify error contains raw response."""
        from app.src.skills.script_generation import run_script_generation

        raw_malformed = "This is not JSON at all!!"
        adapter = _make_llm_adapter(raw_malformed)

        with pytest.raises(LLMParseError) as exc_info:
            run_script_generation(
                input_kind="topic",
                input_text="test topic",
                llm_adapter=adapter,
            )

        # Error must preserve raw response for debugging
        assert raw_malformed in str(exc_info.value) or hasattr(exc_info.value, "__cause__")

    def test_generate_script_llm_error(self) -> None:
        """Mock LLM failure, verify error propagates."""
        from app.src.skills.script_generation import run_script_generation

        adapter = MagicMock()
        adapter.chat.side_effect = LLMApiError("Server error (HTTP 503)")

        with pytest.raises(LLMApiError) as exc_info:
            run_script_generation(
                input_kind="topic",
                input_text="test topic",
                llm_adapter=adapter,
            )

        assert exc_info.value.error_category == "api_error"


# ---------------------------------------------------------------------------
# StepRunner dispatch tests
# ---------------------------------------------------------------------------

class TestStepRunnerDispatch:
    """Tests verifying StepRunner uses skill dispatch for script_generation."""

    def test_step_runner_dispatches_script_generation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """StepRunner should dispatch to run_script_generation skill via STEP_SKILLS."""
        store = SqliteStore(":memory:")
        artifacts = ArtifactStore(str(tmp_path / "artifacts"))

        # Patch LLMAdapter.from_env to return a mock
        mock_adapter = _make_llm_adapter(_valid_script_json())
        monkeypatch.setattr("app.src.workers.step_runner.LLMAdapter.from_env", lambda: mock_adapter)

        runner = StepRunner(store=store, artifact_store=artifacts)

        task = store.create_task(
            video_type="knowledge_share",
            input_kind="topic",
            input_text="How to learn effectively",
            source_links=[],
        )
        store.init_steps(task.id, ["script_generation"])

        executed = runner.run_step(task_id=task.id, step_key="script_generation")
        assert executed is True

        step = store.get_step(task.id, "script_generation")
        assert step is not None
        assert step.status == StepStatus.completed

        # Verify llm_adapter.chat was called (skill was dispatched)
        mock_adapter.chat.assert_called_once()

        # Verify artifacts were written
        rows = store.list_artifacts(task.id)
        assert len(rows) >= 1
        artifact_types = [a.artifact_type.value for a in rows]
        assert "parsed_json" in artifact_types or "llm_raw" in artifact_types

    def test_step_runner_script_generation_writes_llm_raw_artifact(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """StepRunner should write llm_raw artifact alongside parsed_json."""
        store = SqliteStore(":memory:")
        artifacts = ArtifactStore(str(tmp_path / "artifacts"))

        mock_adapter = _make_llm_adapter(_valid_script_json())
        monkeypatch.setattr("app.src.workers.step_runner.LLMAdapter.from_env", lambda: mock_adapter)

        runner = StepRunner(store=store, artifact_store=artifacts)

        task = store.create_task(
            video_type="knowledge_share",
            input_kind="topic",
            input_text="Test topic",
            source_links=[],
        )
        store.init_steps(task.id, ["script_generation"])

        runner.run_step(task_id=task.id, step_key="script_generation")

        rows = store.list_artifacts(task.id)
        artifact_types = [a.artifact_type.value for a in rows]
        assert "llm_raw" in artifact_types, f"Expected llm_raw artifact, got: {artifact_types}"
        assert "parsed_json" in artifact_types, f"Expected parsed_json artifact, got: {artifact_types}"

    def test_step_runner_script_generation_failure_sets_step_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When LLM fails, step should be marked as failed."""
        store = SqliteStore(":memory:")
        artifacts = ArtifactStore(str(tmp_path / "artifacts"))

        mock_adapter = MagicMock()
        mock_adapter.chat.side_effect = LLMApiError("Server error (HTTP 500)")
        monkeypatch.setattr("app.src.workers.step_runner.LLMAdapter.from_env", lambda: mock_adapter)

        runner = StepRunner(store=store, artifact_store=artifacts)

        task = store.create_task(
            video_type="knowledge_share",
            input_kind="topic",
            input_text="Test topic",
            source_links=[],
        )
        store.init_steps(task.id, ["script_generation"])

        executed = runner.run_step(task_id=task.id, step_key="script_generation")
        assert executed is True

        step = store.get_step(task.id, "script_generation")
        assert step is not None
        assert step.status == StepStatus.failed
        assert step.error_category is not None
