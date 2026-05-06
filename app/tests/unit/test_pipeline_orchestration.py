"""Unit tests for pipeline orchestration constants and logic in video_tasks.py."""
from __future__ import annotations

from app.src.server.routes.video_tasks import DEFAULT_STEP_KEYS


class TestDefaultStepKeys:
    """Verify DEFAULT_STEP_KEYS is correctly configured for the 9-step pipeline."""

    def test_default_step_keys_count(self) -> None:
        assert len(DEFAULT_STEP_KEYS) == 9

    def test_default_step_keys_order(self) -> None:
        assert DEFAULT_STEP_KEYS[0] == "material_fetch"
        assert DEFAULT_STEP_KEYS[-1] == "video_compose"
        assert DEFAULT_STEP_KEYS == [
            "material_fetch",
            "script_generation",
            "storyboard",
            "review_script",
            "voiceover",
            "material_extract",
            "material_match",
            "subtitle",
            "video_compose",
        ]

    def test_default_step_keys_contains_media_steps(self) -> None:
        media_steps = {"voiceover", "material_extract", "material_match", "subtitle", "video_compose"}
        step_set = set(DEFAULT_STEP_KEYS)
        for step in media_steps:
            assert step in step_set, f"{step} missing from DEFAULT_STEP_KEYS"

    def test_default_step_keys_material_fetch_first(self) -> None:
        assert DEFAULT_STEP_KEYS[0] == "material_fetch"

    def test_default_step_keys_llm_steps_before_media(self) -> None:
        """LLM steps (script_generation, storyboard, review_script) come before media steps."""
        llm_steps = ["script_generation", "storyboard", "review_script"]
        media_start = DEFAULT_STEP_KEYS.index("voiceover")
        for step in llm_steps:
            idx = DEFAULT_STEP_KEYS.index(step)
            assert idx < media_start, f"{step} should come before voiceover but is at index {idx}"
