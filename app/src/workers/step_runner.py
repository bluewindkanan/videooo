from __future__ import annotations

import json
import threading
from typing import Callable, Optional

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import ArtifactType, StepStatus, TaskStatus
from app.src.skills.llm_adapter import LLMAdapter, LLMError
from app.src.skills.material_fetch import MaterialFetchResult, run_material_fetch
from app.src.skills.script_generation import run_script_generation
from app.src.skills.storyboard import run_storyboard
from app.src.skills.review_script import run_review_script
from app.src.skills.voiceover import run_voiceover
from app.src.skills.material_extract import run_material_extract
from app.src.skills.material_match import run_material_match
from app.src.skills.subtitle import run_subtitle
from app.src.skills.video_compose import run_video_compose
from app.src.storage.sqlite import SqliteStore


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_key(task_id: str, step_key: str) -> str:
    return f"{task_id}:{step_key}"


def _get_lock(task_id: str, step_key: str) -> threading.Lock:
    key = _lock_key(task_id, step_key)
    with _locks_guard:
        if key not in _locks:
            _locks[key] = threading.Lock()
        return _locks[key]


# ---------------------------------------------------------------------------
# Skill dispatch registry
# ---------------------------------------------------------------------------

STEP_SKILLS: dict[str, Callable[..., object]] = {
    "material_fetch": run_material_fetch,
    "script_generation": run_script_generation,
    "storyboard": run_storyboard,
    "review_script": run_review_script,
    "voiceover": run_voiceover,
    "material_extract": run_material_extract,
    "material_match": run_material_match,
    "subtitle": run_subtitle,
    "video_compose": run_video_compose,
}


class MaterialFetchAllFailed(Exception):
    """Raised when all source links fail to download."""
    def __init__(self, results: list[MaterialFetchResult]) -> None:
        self.results = results
        super().__init__("all_source_links_failed")


class StepRunner:
    def __init__(
        self,
        *,
        store: SqliteStore,
        artifact_store: ArtifactStore,
        llm_adapter: Optional[LLMAdapter] = None,
    ) -> None:
        self.store = store
        self.artifacts = artifact_store
        self.llm_adapter = llm_adapter if llm_adapter is not None else LLMAdapter.from_env()

    def run_step(self, *, task_id: str, step_key: str) -> bool:
        """Run a step once. Returns True if executed, False if skipped (e.g., locked)."""
        lock = _get_lock(task_id, step_key)
        if not lock.acquire(blocking=False):
            return False
        try:
            step = self.store.get_step(task_id, step_key)
            if not step:
                return False

            self.store.set_step_status(task_id, step_key, StepStatus.running)

            task = self.store.get_task(task_id)
            if not task:
                self.store.set_step_failed(
                    task_id, step_key, error_category="non_retryable", error_message="task_not_found"
                )
                return True

            input_text = task.input_text or ""

            # Deterministic failure injection: first attempt fails when input contains FAIL,
            # second attempt (after retry) succeeds.
            if "FAIL" in input_text.upper() and step.retry_count == 0:
                self.store.set_step_failed(
                    task_id,
                    step_key,
                    error_category="needs_user_action",
                    error_message="simulated failure (contains FAIL)",
                )
                return True

            # Dispatch to registered skill
            skill_fn = STEP_SKILLS.get(step_key)
            if skill_fn is None:
                self.store.set_step_failed(
                    task_id,
                    step_key,
                    error_category="non_retryable",
                    error_message=f"unknown_step_key:{step_key}",
                )
                return True

            try:
                result = self._run_skill(skill_fn, task_id=task_id, step_key=step_key, task=task)
            except LLMError as exc:
                self.store.set_step_failed(
                    task_id,
                    step_key,
                    error_category=exc.error_category,
                    error_message=str(exc),
                )
                return True
            except MaterialFetchAllFailed:
                # Step already marked failed + task set to waiting_for_material in _run_material_fetch
                return True
            except Exception as exc:
                # Catch-all: mark step as failed so pipeline can continue
                self.store.set_step_failed(
                    task_id,
                    step_key,
                    error_category="skill_error",
                    error_message=str(exc),
                )
                return True

            self.store.set_step_status(task_id, step_key, StepStatus.completed, progress_percent=100)
            return True
        finally:
            lock.release()

    def _run_skill(
        self,
        skill_fn: Callable[..., object],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> object:
        """Execute a skill function, write artifacts, and return the result."""
        if step_key == "material_fetch":
            return self._run_material_fetch(skill_fn, task_id=task_id, step_key=step_key, task=task)

        if step_key == "script_generation":
            return self._run_script_generation(skill_fn, task_id=task_id, step_key=step_key, task=task)

        if step_key == "storyboard":
            return self._run_storyboard(skill_fn, task_id=task_id, step_key=step_key, task=task)

        if step_key == "review_script":
            return self._run_review_script(skill_fn, task_id=task_id, step_key=step_key, task=task)

        if step_key == "voiceover":
            return self._run_voiceover(skill_fn, task_id=task_id, step_key=step_key, task=task)

        if step_key == "material_extract":
            return self._run_material_extract(skill_fn, task_id=task_id, step_key=step_key, task=task)

        if step_key == "material_match":
            return self._run_material_match(skill_fn, task_id=task_id, step_key=step_key, task=task)

        if step_key == "subtitle":
            return self._run_subtitle(skill_fn, task_id=task_id, step_key=step_key, task=task)

        if step_key == "video_compose":
            return self._run_video_compose(skill_fn, task_id=task_id, step_key=step_key, task=task)

        result = skill_fn()
        return result

    def _run_material_fetch(
        self,
        skill_fn: Callable[..., object],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> list:
        """Run material_fetch skill: download source links, write status artifact."""
        source_links_json = getattr(task, "source_links_json", "[]")
        source_links = json.loads(source_links_json) if source_links_json else []

        if not source_links:
            # No links — step completes immediately
            return []

        results = skill_fn(
            source_links=source_links,
            artifact_store=self.artifacts,
            task_id=task_id,
        )

        # Write material_status artifact
        status_payload = [
            {
                "url": r.url,
                "status": r.status,
                "failure_category": r.failure_category,
                "failure_message": r.failure_message,
                "storage_ref": r.storage_ref,
                "file_size": r.file_size,
                "content_type": r.content_type,
            }
            for r in results
        ]
        ref = self.artifacts.write_json(
            task_id=task_id,
            step_key=step_key,
            artifact_type="material_status",
            payload=status_payload,
        )
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.material_status,
            storage_ref=ref.storage_ref,
            metadata={"kind": "material_status", "link_count": len(source_links)},
        )

        # Write source_video artifacts for successful downloads
        for r in results:
            if r.status == "success" and r.storage_ref:
                self.store.add_artifact(
                    task_id=task_id,
                    step_key=step_key,
                    artifact_type=ArtifactType.source_video,
                    storage_ref=r.storage_ref,
                    metadata={"source_url": r.url, "file_size": r.file_size, "content_type": r.content_type},
                )

        # Determine分流
        all_failed = all(r.status == "failed" for r in results) if results else False
        if all_failed:
            self.store.set_step_failed(
                task_id, step_key,
                error_category="needs_user_action",
                error_message="all_source_links_failed",
            )
            self.store.set_task_status(task_id, TaskStatus.waiting_for_material)
            raise MaterialFetchAllFailed(results)

        return results

    def _run_script_generation(
        self,
        skill_fn: Callable[..., dict],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> dict:
        """Run script_generation skill with LLM raw capture and artifact writing."""
        input_kind = getattr(task, "input_kind", "topic")
        input_text = getattr(task, "input_text", "") or ""

        # Capture raw LLM response by wrapping the adapter
        captured: list[str] = []
        original_chat = self.llm_adapter.chat

        def _capturing_chat(*, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
            text = original_chat(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens)
            captured.append(text)
            return text

        # Temporarily swap chat to capture raw response
        self.llm_adapter.chat = _capturing_chat  # type: ignore[assignment]
        try:
            result = skill_fn(
                input_kind=input_kind,
                input_text=input_text,
                llm_adapter=self.llm_adapter,
            )
        finally:
            self.llm_adapter.chat = original_chat  # type: ignore[assignment]

        # Write llm_raw artifact
        if captured:
            raw_ref = self.artifacts.write_json(
                task_id=task_id,
                step_key=step_key,
                artifact_type="llm_raw",
                payload={"raw_response": captured[0]},
            )
            self.store.add_artifact(
                task_id=task_id,
                step_key=step_key,
                artifact_type=ArtifactType.llm_raw,
                storage_ref=raw_ref.storage_ref,
                metadata={"kind": "llm_raw"},
            )

        # Write parsed_json artifact
        ref = self.artifacts.write_json(
            task_id=task_id,
            step_key=step_key,
            artifact_type="script_draft",
            payload=result,
        )
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.parsed_json,
            storage_ref=ref.storage_ref,
            metadata={"kind": "script_draft"},
        )
        return result

    def _run_storyboard(
        self,
        skill_fn: Callable[..., object],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> list:
        """Run storyboard skill: read script artifact, generate segments, write artifacts."""
        script_draft = self._read_latest_artifact_payload(task_id, "script_generation", "parsed_json")
        if script_draft is None:
            raise LLMError("script_draft artifact not found", error_category="non_retryable")

        captured: list[str] = []
        original_chat = self.llm_adapter.chat

        def _capturing_chat(*, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
            text = original_chat(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens)
            captured.append(text)
            return text

        self.llm_adapter.chat = _capturing_chat  # type: ignore[assignment]
        try:
            result = skill_fn(script_draft=script_draft, llm_adapter=self.llm_adapter)
        finally:
            self.llm_adapter.chat = original_chat  # type: ignore[assignment]

        if captured:
            raw_ref = self.artifacts.write_json(
                task_id=task_id, step_key=step_key, artifact_type="llm_raw",
                payload={"raw_response": captured[0]},
            )
            self.store.add_artifact(
                task_id=task_id, step_key=step_key, artifact_type=ArtifactType.llm_raw,
                storage_ref=raw_ref.storage_ref, metadata={"kind": "llm_raw"},
            )

        ref = self.artifacts.write_json(
            task_id=task_id, step_key=step_key, artifact_type="storyboard_segments",
            payload=result,
        )
        self.store.add_artifact(
            task_id=task_id, step_key=step_key, artifact_type=ArtifactType.parsed_json,
            storage_ref=ref.storage_ref, metadata={"kind": "storyboard_segments"},
        )
        return result

    def _run_review_script(
        self,
        skill_fn: Callable[..., object],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> list:
        """Run review_script skill: read script + storyboard artifacts, generate findings, write artifacts."""
        script_draft = self._read_latest_artifact_payload(task_id, "script_generation", "parsed_json")
        storyboard_segments = self._read_latest_artifact_payload(task_id, "storyboard", "parsed_json")
        if script_draft is None:
            raise LLMError("script_draft artifact not found", error_category="non_retryable")

        captured: list[str] = []
        original_chat = self.llm_adapter.chat

        def _capturing_chat(*, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
            text = original_chat(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens)
            captured.append(text)
            return text

        self.llm_adapter.chat = _capturing_chat  # type: ignore[assignment]
        try:
            result = skill_fn(
                script_draft=script_draft,
                storyboard_segments=storyboard_segments or [],
                llm_adapter=self.llm_adapter,
            )
        finally:
            self.llm_adapter.chat = original_chat  # type: ignore[assignment]

        if captured:
            raw_ref = self.artifacts.write_json(
                task_id=task_id, step_key=step_key, artifact_type="llm_raw",
                payload={"raw_response": captured[0]},
            )
            self.store.add_artifact(
                task_id=task_id, step_key=step_key, artifact_type=ArtifactType.llm_raw,
                storage_ref=raw_ref.storage_ref, metadata={"kind": "llm_raw"},
            )

        ref = self.artifacts.write_json(
            task_id=task_id, step_key=step_key, artifact_type="review_findings",
            payload=result,
        )
        self.store.add_artifact(
            task_id=task_id, step_key=step_key, artifact_type=ArtifactType.review,
            storage_ref=ref.storage_ref, metadata={"kind": "review_findings"},
        )
        return result

    def _run_voiceover(
        self,
        skill_fn: Callable[..., object],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> dict:
        """Run voiceover skill: read storyboard artifact, generate TTS audio, write artifacts."""
        storyboard_segments = self._read_latest_artifact_payload(task_id, "storyboard", "parsed_json")
        if storyboard_segments is None:
            raise LLMError("storyboard_segments artifact not found", error_category="non_retryable")

        result = skill_fn(
            storyboard_segments=storyboard_segments,
            artifact_store=self.artifacts,
            task_id=task_id,
        )

        # Register per-segment audio files as audio artifacts
        for seg in result["segments"]:
            self.store.add_artifact(
                task_id=task_id,
                step_key=step_key,
                artifact_type=ArtifactType.audio,
                storage_ref=seg["segment_audio_ref"],
                metadata={
                    "kind": "segment_audio",
                    "segment_index": seg["segment_index"],
                    "duration_seconds": seg["duration_seconds"],
                },
            )

        # Register full audio as audio artifact
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.audio,
            storage_ref=result["full_audio_ref"],
            metadata={"kind": "full_voiceover", "total_duration_seconds": result["total_duration_seconds"]},
        )

        # Write timing_data as parsed_json artifact
        timing_ref = self.artifacts.write_json(
            task_id=task_id,
            step_key=step_key,
            artifact_type="voiceover_timing",
            payload=result,
        )
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.parsed_json,
            storage_ref=timing_ref.storage_ref,
            metadata={"kind": "voiceover_timing"},
        )

        return result

    def _run_material_extract(
        self,
        skill_fn: Callable[..., object],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> dict:
        """Run material_extract skill: read source_video artifacts, extract clips, write artifacts."""
        # Collect source_video storage_refs from material_fetch step
        artifacts = self.store.list_artifacts(task_id)
        source_video_refs = [
            a.storage_ref
            for a in artifacts
            if a.step_key == "material_fetch" and a.artifact_type == ArtifactType.source_video
        ]

        manifest = skill_fn(
            source_video_refs=source_video_refs,
            artifact_store=self.artifacts,
            task_id=task_id,
        )

        # Register each clip as a clip artifact
        for clip in manifest["clips"]:
            self.store.add_artifact(
                task_id=task_id,
                step_key=step_key,
                artifact_type=ArtifactType.clip,
                storage_ref=clip["storage_ref"],
                metadata={
                    "kind": "clip",
                    "clip_index": clip["clip_index"],
                    "source_ref": clip["source_ref"],
                    "start_seconds": clip["start_seconds"],
                    "end_seconds": clip["end_seconds"],
                    "duration_seconds": clip["duration_seconds"],
                },
            )

        # Write clip_manifest as parsed_json artifact
        manifest_ref = self.artifacts.write_json(
            task_id=task_id,
            step_key=step_key,
            artifact_type="clip_manifest",
            payload=manifest,
        )
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.parsed_json,
            storage_ref=manifest_ref.storage_ref,
            metadata={"kind": "clip_manifest"},
        )

        return manifest

    def _run_material_match(
        self,
        skill_fn: Callable[..., object],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> dict:
        """Run material_match skill: read voiceover_timing + clip_manifest, compute assignments."""
        voiceover_timing = self._read_latest_artifact_payload(task_id, "voiceover", "parsed_json")
        clip_manifest = self._read_latest_artifact_payload(task_id, "material_extract", "parsed_json")

        result = skill_fn(
            voiceover_timing=voiceover_timing or {"segments": []},
            clip_manifest=clip_manifest or {"clips": []},
        )

        # Write matched_segments as parsed_json artifact
        ref = self.artifacts.write_json(
            task_id=task_id,
            step_key=step_key,
            artifact_type="matched_segments",
            payload=result,
        )
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.parsed_json,
            storage_ref=ref.storage_ref,
            metadata={"kind": "matched_segments"},
        )

        return result

    def _run_subtitle(
        self,
        skill_fn: Callable[..., object],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> dict:
        """Run subtitle skill: read voiceover timing, generate SRT, write artifacts."""
        voiceover_timing = self._read_latest_artifact_payload(task_id, "voiceover", "parsed_json")
        if voiceover_timing is None:
            raise LLMError("voiceover_timing artifact not found", error_category="non_retryable")

        result = skill_fn(
            voiceover_timing=voiceover_timing,
            artifact_store=self.artifacts,
            task_id=task_id,
        )

        # Register .srt file as subtitle artifact
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.subtitle,
            storage_ref=result["srt_ref"],
            metadata={
                "kind": "subtitle",
                "entry_count": result["entry_count"],
                "total_duration_seconds": result["total_duration_seconds"],
                "source": result["source"],
            },
        )

        # Write subtitle_metadata as parsed_json artifact
        metadata_ref = self.artifacts.write_json(
            task_id=task_id,
            step_key=step_key,
            artifact_type="subtitle_metadata",
            payload=result,
        )
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.parsed_json,
            storage_ref=metadata_ref.storage_ref,
            metadata={"kind": "subtitle_metadata"},
        )

        return result

    def _run_video_compose(
        self,
        skill_fn: Callable[..., object],
        *,
        task_id: str,
        step_key: str,
        task: object,
    ) -> dict:
        """Run video_compose skill: read matched_segments + voiceover + subtitle + clips, compose final video."""
        matched_segments = self._read_latest_artifact_payload(task_id, "material_match", "parsed_json")
        voiceover_timing = self._read_latest_artifact_payload(task_id, "voiceover", "parsed_json")
        clip_manifest = self._read_latest_artifact_payload(task_id, "material_extract", "parsed_json")

        # Get subtitle storage_ref path (the .srt file)
        artifacts = self.store.list_artifacts(task_id)
        subtitle_artifacts = [
            a for a in artifacts
            if a.step_key == "subtitle" and a.artifact_type == ArtifactType.subtitle
        ]
        subtitle_ref = subtitle_artifacts[-1].storage_ref if subtitle_artifacts else ""

        result = skill_fn(
            matched_segments=matched_segments or {"matches": [], "fallback_mode": True},
            voiceover_timing=voiceover_timing or {"total_duration_seconds": 0, "full_audio_ref": ""},
            subtitle_ref=subtitle_ref,
            clip_manifest=clip_manifest or {"clips": []},
            artifact_store=self.artifacts,
            task_id=task_id,
        )

        # Register final_video artifact
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.final_video,
            storage_ref=result["storage_ref"],
            metadata={
                "kind": "final_video",
                "duration_seconds": result["duration_seconds"],
                "resolution": result["resolution"],
                "fallback_mode": result["fallback_mode"],
            },
        )

        # Write compose_log as parsed_json artifact
        log_ref = self.artifacts.write_json(
            task_id=task_id,
            step_key=step_key,
            artifact_type="compose_log",
            payload=result,
        )
        self.store.add_artifact(
            task_id=task_id,
            step_key=step_key,
            artifact_type=ArtifactType.parsed_json,
            storage_ref=log_ref.storage_ref,
            metadata={"kind": "compose_log"},
        )

        return result

    def _read_latest_artifact_payload(
        self, task_id: str, step_key: str, artifact_type: str,
    ) -> object | None:
        """Read the latest artifact payload for a given task/step/type."""
        artifacts = self.store.list_artifacts(task_id)
        matching = [a for a in artifacts if a.step_key == step_key and a.artifact_type.value == artifact_type]
        if not matching:
            return None
        latest = matching[-1]
        try:
            import pathlib
            data = pathlib.Path(latest.storage_ref).read_text(encoding="utf-8")
            import json as _json
            return _json.loads(data)
        except Exception:
            return None
