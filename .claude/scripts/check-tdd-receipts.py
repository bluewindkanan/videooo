#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--tasks', required=True)
    p.add_argument('--receipts', required=True)
    p.add_argument('--schema', default='.bewater/contracts/tdd-receipt.schema.json')
    return p.parse_args()


def completed_implementation_task_ids(text: str) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and re.fullmatch(r"T\d{3}", cells[0]) and cells[1].lower() == "done" and cells[3] == "implementation":
            if cells[0] not in seen:
                ids.append(cells[0])
                seen.add(cells[0])
        m = re.match(r"^- \[(x|X)\] (T\d{3})", line.strip())
        if m and m.group(2) not in seen:
            ids.append(m.group(2))
            seen.add(m.group(2))
    return ids


def completed_task_ids(text: str) -> list[str]:
    return completed_implementation_task_ids(text)


BLACKBOX_VERIFY_MARKERS = (
    "curl ",
    "playwright test",
    "cypress run",
    "newman run",
    "pytest tests/e2e",
    "pytest e2e",
    "npm run test:e2e",
)


def task_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^\s*#{3,4}\s+(T\d{3})[:：].*$", text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[match.start():end]
    return blocks


def task_requires_blackbox(block: str) -> bool:
    lowered = block.lower()
    return "blackbox_smoke" in lowered or "formal_e2e" in lowered or "e2e asset" in lowered


def blackbox_required_task_ids(text: str) -> set[str]:
    return {task_id for task_id, block in task_blocks(text).items() if task_requires_blackbox(block)}


def receipt_has_blackbox_verify(receipt: dict) -> bool:
    commands = receipt.get("verify_commands", [])
    if not isinstance(commands, list):
        return False
    combined = "\n".join(str(command).lower() for command in commands)
    return any(marker in combined for marker in BLACKBOX_VERIFY_MARKERS)


def validate_receipt_shape(receipt: dict, task_id: str) -> list[str]:
    errs = []
    required = (
        "task_id",
        "red_command",
        "red_exit_code",
        "red_failure_marker",
        "green_command",
        "green_exit_code",
        "verify_commands",
        "files_under_test",
        "files_changed",
        "recorded_at",
    )
    for key in required:
        if key not in receipt:
            errs.append(f"{task_id}: missing {key}")
    if receipt.get('task_id') != task_id:
        errs.append(f'{task_id}: receipt task_id mismatch')
    if "red_exit_code" in receipt and not isinstance(receipt["red_exit_code"], int):
        errs.append(f"{task_id}: red_exit_code must be integer")
    if "green_exit_code" in receipt and not isinstance(receipt["green_exit_code"], int):
        errs.append(f"{task_id}: green_exit_code must be integer")
    for key in ("verify_commands", "files_under_test", "files_changed"):
        if key in receipt and not isinstance(receipt[key], list):
            errs.append(f"{task_id}: {key} must be array")
    return errs


def main() -> int:
    args = parse_args()
    tasks_text = Path(args.tasks).read_text(encoding='utf-8')
    done_ids = completed_task_ids(tasks_text)
    blackbox_ids = blackbox_required_task_ids(tasks_text)
    receipts_path = Path(args.receipts)

    errors: list[str] = []
    if not receipts_path.exists():
        errors.append(f'receipts file not found: {receipts_path}')
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    try:
        receipts_data = json.loads(receipts_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        errors.append(f'invalid receipts JSON ({exc})')
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    if not isinstance(receipts_data, dict):
        errors.append('receipts.json must be an object keyed by task id')
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    for task_id in done_ids:
        if task_id not in receipts_data:
            errors.append(f'{task_id}: missing receipt key in receipts.json')
            continue
        data = receipts_data[task_id]
        if not isinstance(data, dict):
            errors.append(f'{task_id}: receipt must be object')
            continue
        errors.extend(validate_receipt_shape(data, task_id))
        if task_id in blackbox_ids and not receipt_has_blackbox_verify(data):
            errors.append(f"{task_id}: black-box task receipt must include a black-box verify command")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print('tdd receipt check passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
