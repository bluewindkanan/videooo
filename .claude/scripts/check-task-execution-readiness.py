#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TASK_ID_RE = r"T-?\d{3}"

REQUIRED_BLOCK_MARKERS = [
    "**Story / scenario refs**",
    "**Design refs**",
    "**Exact files in scope**",
    "**Callsites / reuse checklist**",
    "**RED command**",
    "**Expected RED failure marker**",
    "**GREEN target**",
    "**Verify commands**",
    "**Receipt path**",
    "**Done definition**",
    "**Escalation notes**",
]

E2E_BLOCK_MARKERS = [
    "**Test level**",
    "**E2E asset**",
    "**E2E runtime**",
    "**Evidence artifacts**",
]

PLACEHOLDER_PATTERNS = [
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\bUNFILLED\b", re.IGNORECASE),
    re.compile(r"\[说明\]"),
    re.compile(r"\[待补\]"),
    re.compile(r"\[填写\]"),
    re.compile(r"\[测试文件路径\]"),
    re.compile(r"\[实现文件路径\]"),
    re.compile(r"\[(?:N|X)\]"),
    re.compile(r"to be decided", re.IGNORECASE),
    re.compile(r"fill in", re.IGNORECASE),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ready tasks in a BeWater tasks.md file.")
    parser.add_argument("--tasks", required=True, help="Path to tasks.md")
    parser.add_argument(
        "--require-build-complete",
        action="store_true",
        help="Reject final review when any planned task remains unfinished.",
    )
    return parser.parse_args()


def split_task_blocks(text: str) -> list[str]:
    matches = sorted(
        [
            *re.finditer(rf"(?m)^- \[.\]\s+{TASK_ID_RE}.*$", text),
            *re.finditer(rf"(?m)^#{{2,4}}\s+{TASK_ID_RE}[:：].*$", text),
        ],
        key=lambda match: match.start(),
    )
    blocks: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append(text[start:end])
    return blocks


def section_content(block: str, marker: str) -> str:
    start = block.find(marker)
    if start == -1:
        return ""
    rest = block[start + len(marker):]
    next_heading = re.search(r"(?m)^\*\*[^*\n]+\*\*", rest)
    if next_heading:
        rest = rest[: next_heading.start()]
    return rest.strip()


def contains_placeholder(value: str) -> bool:
    return any(pattern.search(value) for pattern in PLACEHOLDER_PATTERNS)


def command_is_too_generic(value: str) -> bool:
    commands = re.findall(r"`([^`]+)`", value)
    if not commands:
        return True
    generic = {"pytest", "npm test", "npm run test", "python3 -m pytest"}
    return any(command.strip() in generic for command in commands)


def has_story_refs(value: str) -> bool:
    lowered = value.lower()
    has_story = "story" in lowered or "story_id" in lowered
    has_scenario = "scenario" in lowered or "acceptance" in lowered
    return has_story and has_scenario


def task_id_from_block(block: str) -> str:
    match = re.search(rf"\b{TASK_ID_RE}\b", block)
    return match.group(0) if match else "unknown"


def normalized_task_id(task_id: str) -> str:
    return task_id.replace("-", "")


def task_status(block: str) -> str:
    status = re.search(r"task_readiness\**\s*:\s*`?([a-z_]+)`?", block, re.IGNORECASE)
    if status:
        return status.group(1).lower()
    checkbox = re.match(r"(?m)^- \[(?P<mark>[xX ])\]", block)
    if checkbox and checkbox.group("mark").lower() == "x":
        return "done"
    return "unknown"


def dependency_ids(block: str) -> list[str]:
    deps: list[str] = []
    for line in block.splitlines():
        lowered = line.lower()
        if "depend" in lowered or "依赖" in line:
            deps.extend(re.findall(rf"\b{TASK_ID_RE}\b", line))
    return deps


def check_build_complete(blocks: list[str]) -> list[str]:
    statuses = {normalized_task_id(task_id_from_block(block)): task_status(block) for block in blocks}
    errors: list[str] = []
    for block in blocks:
        task_id = task_id_from_block(block)
        status = task_status(block)
        if status == "done":
            continue

        deps = [normalized_task_id(dep) for dep in dependency_ids(block)]
        deps_done = all(statuses.get(dep) == "done" for dep in deps)
        if deps_done:
            errors.append(
                f"unfinished planned task {task_id} is dispatchable; do not enter final review before implementing it"
            )
        else:
            errors.append(f"unfinished planned task {task_id} has task_readiness={status}")
    return errors


def block_claims_e2e(block: str) -> bool:
    lowered = block.lower()
    return (
        "test mapping:" in lowered and ("e2e" in lowered or "blackbox_smoke" in lowered)
    ) or (
        "**test level**" in lowered and ("e2e" in lowered or "blackbox_smoke" in lowered)
    ) or (
        "e2e test:" in lowered
    ) or (
        "blackbox_smoke" in lowered
    )


def e2e_asset_is_concrete(value: str) -> bool:
    lowered = value.lower()
    has_driver = "driver:" in lowered
    has_formal_spec = re.search(r"`?[^`\s]+\.spec\.(?:ts|tsx|js|mjs|py)`?", value) is not None
    has_smoke_command = "smoke command:" in lowered and "curl " in lowered
    has_scenario = "scenario" in lowered and re.search(r"\bS-\d{3}\b", value) is not None
    return has_driver and (has_formal_spec or has_smoke_command) and has_scenario


def e2e_runtime_is_concrete(value: str) -> bool:
    lowered = value.lower()
    has_server_or_na = "web server:" in lowered or "server:" in lowered or "n/a" in lowered
    has_base_or_na = "base url:" in lowered or "base_url:" in lowered or "n/a" in lowered
    has_setup = "data/auth setup:" in lowered or "setup:" in lowered
    return has_server_or_na and has_base_or_na and has_setup


def e2e_artifacts_are_concrete(value: str) -> bool:
    lowered = value.lower()
    artifact_terms = ("trace", "screenshot", "video", "logs", "test-results", "artifact")
    return any(term in lowered for term in artifact_terms)


def main() -> int:
    args = parse_args()
    text = Path(args.tasks).read_text(encoding="utf-8")
    ready_for_build = "- **ready_for_build**: `true`" in text
    task_blocks = split_task_blocks(text)
    ready_blocks = [block for block in task_blocks if task_status(block) == "ready"]

    errors: list[str] = []
    if ready_for_build and not ready_blocks and not args.require_build_complete:
        errors.append("ready_for_build=true 但未找到 task_readiness: ready 的任务")

    if args.require_build_complete:
        errors.extend(check_build_complete(task_blocks))

    for block in ready_blocks:
        for marker in REQUIRED_BLOCK_MARKERS:
            if marker not in block:
                errors.append(f"ready task 缺少字段: {marker}")

        for marker in REQUIRED_BLOCK_MARKERS:
            content = section_content(block, marker)
            if not content:
                errors.append(f"ready task {marker} must not be empty")
                continue
            if contains_placeholder(content):
                errors.append(f"ready task {marker} contains placeholder content")

        for command_marker in ("**RED command**", "**Verify commands**"):
            content = section_content(block, command_marker)
            if content and command_is_too_generic(content):
                errors.append(f"ready task {command_marker} must name a concrete verification target")

        story_content = section_content(block, "**Story / scenario refs**")
        if story_content and not has_story_refs(story_content):
            errors.append("ready task **Story / scenario refs** must include story and scenario/acceptance references")

        if block_claims_e2e(block):
            for marker in E2E_BLOCK_MARKERS:
                if marker not in block:
                    errors.append(f"ready e2e task 缺少字段: {marker}")

            asset_content = section_content(block, "**E2E asset**")
            runtime_content = section_content(block, "**E2E runtime**")
            artifact_content = section_content(block, "**Evidence artifacts**")

            if asset_content and not e2e_asset_is_concrete(asset_content):
                errors.append("ready e2e task **E2E asset** must include driver, spec path, and scenario coverage")
            if runtime_content and not e2e_runtime_is_concrete(runtime_content):
                errors.append("ready e2e task **E2E runtime** must include server/base URL or explicit N/A plus data/auth setup")
            if artifact_content and not e2e_artifacts_are_concrete(artifact_content):
                errors.append("ready e2e task **Evidence artifacts** must name trace, screenshot, video, logs, or artifact paths")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("execution readiness check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
