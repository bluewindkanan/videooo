#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--tier", default="standard")
    args = parser.parse_args()

    source = Path(args.source)
    target = Path(args.target)
    tier_path = source / "tiers" / f"{args.tier}.json"
    data = json.loads(tier_path.read_text(encoding="utf-8"))

    for relative in data["include"]:
        src = source / relative
        dst = target / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    print(f"rendered template tier {args.tier} to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
