#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verdict(gate: str, status: str, blockers: list[str], warnings: list[str], action: str) -> dict:
    return {
        "gate": gate,
        "verdict": status,
        "evaluated_at": now(),
        "evidence_refs": [],
        "blockers": blockers,
        "warnings": warnings,
        "recommended_next_action": action,
    }


def evaluate_ship_precheck(project_root: Path) -> dict:
    state_path = project_root / ".bewater/state.json"
    if not state_path.exists():
        return verdict("ship_precheck_gate", "blocked", [".bewater/state.json missing"], [], "bewater-init")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    artifacts = state.get("artifacts", {})
    runtime = state.get("runtime", {})
    report_path = artifacts.get("validation_report_path")
    validation_outcome = runtime.get("validation_outcome")

    blockers: list[str] = []
    evidence_refs: list[str] = []
    if not report_path:
        blockers.append("validation_report_path missing")
    elif not (project_root / report_path).exists():
        blockers.append(f"validation report missing: {report_path}")
    else:
        evidence_refs.append(report_path)

    if validation_outcome is None:
        blockers.append("runtime.validation_outcome missing")
    if isinstance(validation_outcome, dict):
        classification = validation_outcome.get("classification")
        release_decision = validation_outcome.get("release_decision")
        if classification != "ready_for_precheck":
            blockers.append(f"validation_outcome.classification is {classification!r}, expected 'ready_for_precheck'")
        if release_decision != "go":
            blockers.append(f"validation_outcome.release_decision is {release_decision!r}, expected 'go'")
        outcome_blockers = validation_outcome.get("blockers") or []
        if outcome_blockers:
            blockers.extend([f"validation_outcome blocker: {item}" for item in outcome_blockers])

    result = verdict("ship_precheck_gate", "blocked" if blockers else "pass", blockers, [], "bewater-ship" if blockers else "none")
    result["evidence_refs"] = evidence_refs
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--gate", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    if args.gate == "ship_precheck_gate":
        result = evaluate_ship_precheck(project_root)
    else:
        result = verdict(args.gate, "unknown", [f"unsupported gate {args.gate}"], [], "none")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
