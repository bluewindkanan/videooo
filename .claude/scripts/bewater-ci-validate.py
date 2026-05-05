#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from bewater_ci_common import emit, load_state, require_installed_project


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    require_installed_project(project_root)
    state = load_state(project_root)
    artifacts = state.get("artifacts", {})
    has_feature_context = bool(artifacts.get("feature_path")) and bool(artifacts.get("tasks_path"))
    return emit(
        {
            "invoked_wrapper": "bewater-ci-validate",
            "mode": "validate",
            "current_state": state["current_state"],
            "active_flow": "validate-flow",
            "runtime_subphase": "building.validating",
            "evaluated_gates": ["review_gate", "prebuild_review_gate"],
            "stale_gates": [],
            "artifact_refs": [value for value in artifacts.values() if isinstance(value, str)],
            "outcome_classification": "validation_requested" if has_feature_context else "contract_violation",
            "recommended_next_action": "bewater-ship" if has_feature_context else "bewater-plan",
            "exit_code": 0 if has_feature_context else 1,
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
