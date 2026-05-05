#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from bewater_ci_common import (
    emit,
    load_release_config,
    load_state,
    recommended_action_for_semantic_failures,
    release_plan,
    require_installed_project,
    run_semantic_preflights,
    semantic_preflight_errors,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", choices=["precheck", "release"], default="precheck")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    require_installed_project(project_root)
    state = load_state(project_root)
    release_config = load_release_config(project_root)
    plan = release_plan(release_config)
    release_intent = state.get("runtime", {}).get("release_intent")
    release_requested = isinstance(release_intent, dict) and release_intent.get("intent") == "release"
    release_acknowledged = release_requested and release_intent.get("irreversible_acknowledged") is True
    denied_release = args.mode == "release" and (
        not release_requested or (plan["requires_irreversible_ack"] and not release_acknowledged)
    )
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
    elif denied_release:
        outcome = "denied_release_policy"
        recommended_next_action = "bewater-ship --precheck-only"
    else:
        outcome = "ship_requested"
        recommended_next_action = "none"
    return emit(
        {
            "invoked_wrapper": "bewater-ci-ship",
            "mode": args.mode,
            "current_state": state["current_state"],
            "active_flow": "ship-flow",
            "runtime_subphase": state.get("runtime", {}).get("subphase"),
            "evaluated_gates": ["review_gate", "ship_precheck_gate"],
            "stale_gates": [],
            "semantic_preflights": semantic_preflights,
            "semantic_preflight_errors": semantic_errors,
            "artifact_refs": [],
            "release_plan": plan,
            "outcome_classification": outcome,
            "recommended_next_action": recommended_next_action,
            "exit_code": 1 if denied_release or semantic_failures else 0,
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
