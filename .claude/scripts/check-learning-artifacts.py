#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ALLOWED_SEVERITY = {"must", "should", "could"}
ALLOWED_STATUS = ["open", "accepted", "rejected", "planned", "done"]
REQUIRED = {"id", "severity", "source", "target_file", "problem", "proposed_change", "status", "owner", "decision", "updated_at"}


def load_items(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data.get("items", [])
    if isinstance(data, list):
        return data
    raise ValueError("backlog must be object with items or array")


def validate_items(items: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, item in enumerate(items):
        missing = REQUIRED - set(item)
        for key in sorted(missing):
            errors.append(f"item {index}: missing {key}")
        if item.get("severity") not in ALLOWED_SEVERITY:
            errors.append(f"item {index}: invalid severity {item.get('severity')}")
        if item.get("status") not in ALLOWED_STATUS:
            errors.append(f"item {index}: invalid status {item.get('status')}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backlog", required=True)
    args = parser.parse_args()

    try:
        items = load_items(Path(args.backlog))
    except Exception as exc:
        print(f"invalid backlog: {exc}", file=sys.stderr)
        return 1

    errors = validate_items(items)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("learning artifact check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
