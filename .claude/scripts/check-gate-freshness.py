#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def file_digests(paths: list[str], project_root: Path) -> dict[str, str]:
    results: dict[str, str] = {}
    for relative_path in sorted(paths):
        target = project_root / relative_path
        digest = hashlib.sha256()
        if not target.exists():
            digest.update(f"missing:{relative_path}".encode("utf-8"))
        else:
            digest.update(relative_path.encode("utf-8"))
            digest.update(target.read_bytes())
        results[relative_path] = digest.hexdigest()
    return results


def aggregate_digest(digests: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative_path, value in sorted(digests.items()):
        digest.update(relative_path.encode("utf-8"))
        digest.update(value.encode("utf-8"))
    return digest.hexdigest()


def freshness_for_gate(gate_name: str, gate_payload: dict, project_root: Path) -> dict:
    input_refs = gate_payload.get("input_refs") or gate_payload.get("reviewed_inputs") or []
    stale_reasons = []
    current_per_file: dict[str, str] = {}

    if input_refs:
        current_per_file = file_digests(input_refs, project_root)
        current_digest = aggregate_digest(current_per_file)
        expected_per_file = gate_payload.get("input_digests", {})
        if isinstance(expected_per_file, dict):
            for relative_path, current in current_per_file.items():
                expected = expected_per_file.get(relative_path)
                if expected and expected != current:
                    stale_reasons.append(f"input_digest_changed:{relative_path}")
        if gate_payload.get("input_digest") and gate_payload["input_digest"] != current_digest:
            stale_reasons.append("input_digest_changed")
    else:
        current_digest = gate_payload.get("input_digest", "")


    for evidence_ref in gate_payload.get("evidence_refs", []):
        if not (project_root / evidence_ref).exists():
            stale_reasons.append(f"missing_evidence:{evidence_ref}")

    return {
        "gate": gate_name,
        "freshness": "stale" if stale_reasons else "fresh",
        "current_digest": current_digest,
        "current_input_digests": current_per_file,
        "stale_reasons": stale_reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check BeWater gate freshness from state.json")
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    state = json.loads((project_root / ".bewater" / "state.json").read_text(encoding="utf-8"))
    results = [freshness_for_gate(name, payload, project_root) for name, payload in state.get("gates", {}).items()]
    print(json.dumps({"current_state": state["current_state"], "gate_results": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
