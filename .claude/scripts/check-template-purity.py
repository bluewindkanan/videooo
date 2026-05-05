#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


FORBIDDEN = [
    ".claude/skills/bewater-validate/SKILL.md",
    "tests/test_content.py",
    "Harden execution-contract vocabulary",
    "validate-flow describes release-gate mutation",
    "100x",
    "AP-",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root)
    errors: list[str] = []
    for path in (root / "templates").rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in FORBIDDEN:
            if marker in text:
                errors.append(f"{path.relative_to(root)} contains active-project marker {marker}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("template purity check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
