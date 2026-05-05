#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from bewater_ci_common import (
    emit,
    load_state,
    recommended_action_for_semantic_failures,
    require_installed_project,
    run_semantic_preflights,
    semantic_preflight_errors,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    require_installed_project(project_root)
    state = load_state(project_root)
    checker = Path(__file__).with_name("check-gate-freshness.py")
    result = subprocess.run(
        ["python3", str(checker), "--project-root", str(project_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    freshness = json.loads(result.stdout)
    stale_gates = [item["gate"] for item in freshness["gate_results"] if item["freshness"] == "stale"]
    semantic_preflights = run_semantic_preflights(
        project_root,
        state,
        script_dir=Path(__file__).resolve().parent,
    )
    semantic_failures = [item for item in semantic_preflights if item["exit_code"] != 0]
    semantic_errors = semantic_preflight_errors(semantic_preflights)
    if semantic_failures:
        outcome = "semantic_preflight_failed"
        recommended_next_action = recommended_action_for_semantic_failures(semantic_preflights)
    elif stale_gates:
        outcome = "blocking_gate_stale"
        recommended_next_action = "bewater-ship"
    else:
        outcome = "ok"
        recommended_next_action = "none"
    return emit(
        {
            "invoked_wrapper": "bewater-ci-gate-check",
            "mode": "read-only",
            "current_state": state["current_state"],
            "active_flow": state.get("runtime", {}).get("active_flow"),
            "runtime_subphase": state.get("runtime", {}).get("subphase"),
            "evaluated_gates": [item["gate"] for item in freshness["gate_results"]],
            "stale_gates": stale_gates,
            "semantic_preflights": semantic_preflights,
            "semantic_preflight_errors": semantic_errors,
            "artifact_refs": [],
            "outcome_classification": outcome,
            "recommended_next_action": recommended_next_action,
            "exit_code": 1 if stale_gates or semantic_failures else 0,
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
