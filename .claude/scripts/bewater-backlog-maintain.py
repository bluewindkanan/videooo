#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


ALLOWED = {"open", "accepted", "rejected", "planned", "done"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backlog", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--decision", required=True)
    args = parser.parse_args()

    if args.status not in ALLOWED:
        raise SystemExit(f"invalid status {args.status}")

    path = Path(args.backlog)
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data.get("items", []):
        if item.get("id") == args.id:
            item["status"] = args.status
            item["decision"] = args.decision
            item["updated_at"] = date.today().isoformat()
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"updated {args.id} to {args.status}")
            return 0

    raise SystemExit(f"backlog item not found: {args.id}")


if __name__ == "__main__":
    raise SystemExit(main())
