from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from app.src.artifacts.store import ArtifactStore
from app.src.domain.models import ArtifactType, StepStatus
from app.src.storage.sqlite import SqliteStore
from app.src.workers.step_runner import StepRunner


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="app/evals/001/golden.jsonl")
    p.add_argument("--out", default="app/eval-results/001.json")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--retry", action="store_true")
    return p.parse_args()


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def check_script_schema(draft: Dict[str, Any]) -> bool:
    required = ["hook", "body", "call_to_action", "estimated_duration_seconds"]
    for k in required:
        if k not in draft:
            return False
    if not isinstance(draft["hook"], str) or not draft["hook"].strip():
        return False
    if not isinstance(draft["body"], str) or not draft["body"].strip():
        return False
    if not isinstance(draft["call_to_action"], str) or not draft["call_to_action"].strip():
        return False
    if not isinstance(draft["estimated_duration_seconds"], int) or draft["estimated_duration_seconds"] <= 0:
        return False
    return True


def check_min_quality(draft: Dict[str, Any]) -> bool:
    if len(draft.get("body", "")) < 6:
        return False
    dur = draft.get("estimated_duration_seconds")
    if not isinstance(dur, int):
        return False
    return 10 <= dur <= 120


def run_case(case: Dict[str, Any], *, retry_mode: bool) -> Dict[str, Any]:
    store = SqliteStore(":memory:")
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts = ArtifactStore(str(Path(tmpdir) / "artifacts"))
        runner = StepRunner(store=store, artifact_store=artifacts)

        input_text = str(case.get("input_text", ""))
        task = store.create_task(
            video_type="knowledge_share",
            input_kind=str(case.get("input_kind", "topic")),
            input_text=input_text,
            source_links=list(case.get("source_links", [])),
        )
        store.init_steps(task.id, ["script_generation"])

        if retry_mode:
            # First attempt should fail when input contains FAIL; for retry eval we force it.
            store._connect().execute(
                "UPDATE video_tasks SET input_text = ? WHERE id = ?",
                ("FAIL once", task.id),
            )
            runner.run_step(task_id=task.id, step_key="script_generation")
            step = store.get_step(task.id, "script_generation")
            if not step or step.status != StepStatus.failed:
                return {"ok": False, "reason": "expected_failed_before_retry"}
            store.reset_step_for_retry(task.id, "script_generation")
            runner.run_step(task_id=task.id, step_key="script_generation")

        else:
            runner.run_step(task_id=task.id, step_key="script_generation")

        step2 = store.get_step(task.id, "script_generation")
        if not step2 or step2.status != StepStatus.completed:
            return {"ok": False, "reason": "step_not_completed"}

        artifacts_rows = store.list_artifacts(task.id)
        parsed = [a for a in artifacts_rows if a.artifact_type == ArtifactType.parsed_json]
        if not parsed:
            return {"ok": False, "reason": "missing_parsed_json_artifact"}

        draft_path = Path(parsed[-1].storage_ref)
        if not draft_path.exists():
            return {"ok": False, "reason": "artifact_file_missing"}
        draft = json.loads(draft_path.read_text(encoding="utf-8"))

        schema_ok = check_script_schema(draft)
        quality_ok = check_min_quality(draft)
        return {
            "ok": True,
            "schema_ok": schema_ok,
            "quality_ok": quality_ok,
        }


def main() -> int:
    args = parse_args()
    dataset = load_jsonl(args.dataset)

    results: List[Dict[str, Any]] = []
    for case in dataset:
        results.append(run_case(case, retry_mode=bool(args.retry)))

    schema_pass_rate = sum(1 for r in results if r.get("schema_ok")) / max(1, len(results))
    usefulness_rate = sum(1 for r in results if r.get("quality_ok")) / max(1, len(results))
    overall_ok = all(r.get("ok") for r in results)

    out = {
        "feature_id": "001",
        "eval_id": "001",
        "mode": "retry" if args.retry else "default",
        "case_count": len(results),
        "overall_ok": overall_ok,
        "schema_pass_rate": schema_pass_rate,
        "usefulness_rate": usefulness_rate,
        "cases": results,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.verify:
        if schema_pass_rate < 1.0:
            return 2
        if usefulness_rate < 0.8:
            return 3
        if not overall_ok:
            return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

