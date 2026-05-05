#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def _indent_level(line: str) -> int:
    return len(line) - len(line.lstrip())


def _parse_scalar(value: str) -> object:
    stripped = value.strip().strip('"')
    if stripped == "null":
        return None
    if stripped == "true":
        return True
    if stripped == "false":
        return False
    if stripped == "[]":
        return []
    if re.fullmatch(r"-?\d+", stripped):
        return int(stripped)
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
    return stripped


def frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data: dict[str, Any] = {}
    raw_lines = [raw.rstrip() for raw in parts[1].splitlines() if raw.strip()]
    if not raw_lines:
        return data
    base_indent = min(_indent_level(line) for line in raw_lines)
    lines = [(max(0, _indent_level(line) - base_indent), line.strip()) for line in raw_lines]

    index = 0
    while index < len(lines):
        indent, line = lines[index]
        if indent != 0 or ":" not in line:
            index += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = _parse_scalar(value)
            index += 1
            continue

        next_index = index + 1
        if next_index >= len(lines) or lines[next_index][0] == 0:
            data[key] = None
            index += 1
            continue

        child_indent, child_line = lines[next_index]
        if child_line.startswith("- "):
            items: list[object] = []
            current_item: dict[str, object] | None = None
            while next_index < len(lines) and lines[next_index][0] >= child_indent:
                item_indent, item_line = lines[next_index]
                if item_indent == child_indent and item_line.startswith("- "):
                    item_text = item_line[2:].strip()
                    if ":" in item_text:
                        current_item = {}
                        item_key, item_value = item_text.split(":", 1)
                        current_item[item_key.strip()] = _parse_scalar(item_value)
                        items.append(current_item)
                    else:
                        current_item = None
                        items.append(_parse_scalar(item_text))
                elif current_item is not None and item_indent > child_indent and ":" in item_line:
                    item_key, item_value = item_line.split(":", 1)
                    current_item[item_key.strip()] = _parse_scalar(item_value)
                else:
                    break
                next_index += 1
            data[key] = items
            index = next_index
            continue

        mapping: dict[str, object] = {}
        while next_index < len(lines) and lines[next_index][0] >= child_indent:
            item_indent, item_line = lines[next_index]
            if item_indent != child_indent or ":" not in item_line:
                break
            item_key, item_value = item_line.split(":", 1)
            item_key = item_key.strip()
            item_value = item_value.strip()
            if item_value:
                mapping[item_key] = _parse_scalar(item_value)
                next_index += 1
                continue
            nested_index = next_index + 1
            nested: list[object] = []
            while nested_index < len(lines) and lines[nested_index][0] > item_indent and lines[nested_index][1].startswith("- "):
                nested.append(_parse_scalar(lines[nested_index][1][2:]))
                nested_index += 1
            mapping[item_key] = nested
            next_index = nested_index
        data[key] = mapping
        index = next_index
    return data


def is_blank_or_marker(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return stripped == "" or stripped in {"[描述]", "[说明]", "[功能名]", "{功能名}", "{编号}", "无"}


def is_explicit_na(value: object) -> bool:
    return isinstance(value, str) and value.strip().startswith("N/A — ") and len(value.strip()) > len("N/A — ")


def list_items(value: object) -> list[dict[str, object]]:
    return value if isinstance(value, list) else []


ALLOWED_LIFECYCLE_STATUS = {"active", "superseded", "partially_superseded", "unknown"}

ALLOWED_PRODUCT_PLAN_STATUS = {
    "candidate",
    "recommended",
    "in_goal",
    "active_feature",
    "shipped",
    "blocked",
    "superseded",
}
ALLOWED_PRODUCT_PLAN_PRIORITY = {"P1", "P2", "P3"}
PRODUCT_PLAN_REQUIRED_SECTIONS = (
    "Planning Intent",
    "MVP Learning Loop",
    "Feature Candidate Map",
    "Recommended Next Feature",
    "Dependency / Sequencing Notes",
    "Not Yet Ready Candidates",
    "Completed / Superseded Candidates",
)
TASK_LEVEL_LEAKAGE_MARKERS = (
    "Execution Block",
    "RED command",
    "GREEN target",
    "Verify commands",
    "Modify:",
    "Test:",
    "E2E Test:",
    "receipts.json#T",
)


def implementation_paths(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    paths = []
    for item in value:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if not stripped or is_explicit_na(stripped):
            continue
        paths.append(stripped)
    return paths


def changed_paths_after_commit(project_root: Path, commit: str, paths: list[str]) -> list[str]:
    if not commit or not paths:
        return []
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{commit}..HEAD", "--", *paths],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"docs_freshness_unavailable:{result.stderr.strip() or 'git diff failed'}"]
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def scenario_ids_from_feature(feature_text: str) -> set[str]:
    meta = frontmatter(feature_text)
    scenarios = meta.get("scenarios")
    if isinstance(scenarios, list):
        return {item["id"] for item in scenarios if isinstance(item, dict) and item.get("id")}
    return set(re.findall(r"\bS-\d{3}\b", feature_text))


def markdown_body_without_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2]


def canonical_story_ids_from_text(text: str) -> set[str]:
    return set(re.findall(r"\bUS-\d{3}\b", text))


def canonical_ac_ids_from_text(text: str) -> set[str]:
    return set(re.findall(r"\bAC-\d{3}\b", text))


def noncanonical_story_markers(text: str) -> set[str]:
    markers = set(re.findall(r"(?m)^\s*\|\s*(S\d+)\s*\|", text))
    markers.update(re.findall(r"(?m)^\s*#{2,4}\s+(S\d+)\s*[:：-]", text))
    return markers


def scenario_ids_from_text(text: str) -> set[str]:
    return set(re.findall(r"\bS-\d{3}\b", text))


BLACKBOX_VERIFY_MARKERS = (
    "curl ",
    "playwright test",
    "cypress run",
    "newman run",
    "pytest tests/e2e",
    "pytest e2e",
    "npm run test:e2e",
)

FORMAL_E2E_MARKERS = (
    "playwright test",
    "cypress run",
    "npm run test:e2e",
)


def markdown_commands(text: str) -> list[str]:
    return re.findall(r"`([^`]+)`", text)


def command_haystack(text: str) -> str:
    commands = markdown_commands(text)
    return "\n".join(commands if commands else [text]).lower()


def has_blackbox_verify_command(text: str) -> bool:
    haystack = command_haystack(text)
    return any(marker in haystack for marker in BLACKBOX_VERIFY_MARKERS)


def has_formal_e2e_command(text: str) -> bool:
    haystack = command_haystack(text)
    return any(marker in haystack for marker in FORMAL_E2E_MARKERS)


def markdown_section(text: str, heading: str) -> str:
    match = re.search(rf"(?im)^\s*(#+)\s+{re.escape(heading)}\s*$", text)
    if not match:
        return ""
    level = len(match.group(1))
    section = text[match.end():]
    next_heading = re.search(rf"(?m)^\s*#{{1,{level}}}\s+", section)
    if next_heading:
        section = section[: next_heading.start()]
    return section


def product_plan_candidate_rows(text: str) -> list[dict[str, str]]:
    section = markdown_section(text, "Feature Candidate Map")
    rows: list[dict[str, str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 11 or cells[0] == "ID" or not re.fullmatch(r"PC-\d{3}", cells[0]):
            continue
        rows.append(
            {
                "id": cells[0],
                "title": cells[1],
                "user_value": cells[2],
                "vision_link": cells[3],
                "mvp_role": cells[4],
                "observable_effect": cells[5],
                "feedback_value": cells[6],
                "priority": cells[7],
                "status": cells[8],
                "why_now": cells[9],
                "risk": cells[10],
            }
        )
    return rows


def recommended_product_plan_candidate_id(text: str) -> str | None:
    section = markdown_section(text, "Recommended Next Feature")
    match = re.search(r"(?mi)^-\s*candidate_id:\s*(PC-\d{3})\s*$", section)
    return match.group(1) if match else None


def has_date_based_commitment(text: str) -> bool:
    date_patterns = (
        r"\bby\s+20\d{2}-\d{2}-\d{2}\b",
        r"\bby\s+Q[1-4]\b",
        r"\bQ[1-4]\s+20\d{2}\b",
        r"\b20\d{2}-\d{2}-\d{2}\s*(?:ship|release|launch|上线|发布)",
        r"(?:ship|release|launch|上线|发布)\s+(?:by|before|在|于)\s*20\d{2}-\d{2}-\d{2}",
    )
    lower = text.lower()
    return any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in date_patterns)


def e2e_strategy_rows(design_text: str) -> dict[str, dict[str, str]]:
    section = markdown_section(design_text, "E2E Test Strategy")
    rows: dict[str, dict[str, str]] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2 or not re.fullmatch(r"S-\d{3}", cells[0]):
            continue
        rows[cells[0]] = {
            "required": cells[1],
            "driver": cells[2] if len(cells) > 2 else "",
            "asset": cells[3] if len(cells) > 3 else "",
            "raw": stripped,
        }
    return rows


def e2e_requirement_level(row: dict[str, str]) -> str | None:
    combined = " ".join([row.get("required", ""), row.get("driver", ""), row.get("asset", "")]).lower()
    if "formal_e2e" in combined or "playwright" in combined or ".spec." in combined or combined.startswith("yes"):
        return "formal_e2e"
    if "blackbox_smoke" in combined or "black-box" in combined or "blackbox" in combined or "curl" in combined:
        return "blackbox_smoke"
    if "n/a" in combined or "static_verify" in combined or combined.startswith("no"):
        return None
    return None


def e2e_row_has_explicit_non_blackbox_reason(row: dict[str, str]) -> bool:
    required = row.get("required", "").lower()
    if "n/a" not in required and "static_verify" not in required and not required.startswith("no"):
        return True
    return "—" in row.get("required", "") or "reason" in required or "because" in required


def scenario_task_evidence(tasks_text: str, scenario_id: str) -> str:
    blocks = task_blocks(tasks_text)
    matching_blocks = [block for block in blocks.values() if scenario_id in block]
    matching_rows = [line for line in tasks_text.splitlines() if scenario_id in line]
    return "\n".join([*matching_rows, *matching_blocks])


def task_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^\s*#{3,4}\s+(T\d{3})[:：].*$", text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = text[match.start():end]
    return blocks


def check_feature(args: argparse.Namespace) -> list[str]:
    text = Path(args.feature).read_text(encoding="utf-8")
    meta = frontmatter(text)
    scenarios = meta.get("scenarios")
    errors: list[str] = []
    lifecycle_status = meta.get("lifecycle_status")
    if lifecycle_status is not None and lifecycle_status not in ALLOWED_LIFECYCLE_STATUS:
        errors.append("feature.md lifecycle_status must be active|superseded|partially_superseded|unknown")

    if not isinstance(scenarios, list) or not scenarios:
        errors.append("feature.md must define frontmatter scenarios")
    else:
        for item in scenarios:
            if not isinstance(item, dict):
                errors.append("feature scenario must be an object")
                continue
            for key in ("id", "story_id", "given", "when", "then"):
                if not item.get(key):
                    errors.append(f"feature scenario missing {key}")
            scenario_id = item.get("id")
            story_id = item.get("story_id")
            if scenario_id and not re.fullmatch(r"S-\d{3}", str(scenario_id)):
                errors.append("feature scenario id must use S-xxx format")
            if story_id and not re.fullmatch(r"US-\d{3}", str(story_id)):
                errors.append("scenario story_id must use US-xxx format")
            if not item.get("acceptance_refs"):
                errors.append(f"feature scenario {scenario_id or '<unknown>'} missing acceptance_refs")

    body_text = markdown_body_without_frontmatter(text)
    body_story_ids = canonical_story_ids_from_text(body_text)
    body_ac_ids = canonical_ac_ids_from_text(body_text)
    if not body_story_ids:
        errors.append("feature.md must declare canonical user stories with US-xxx ids")
    if not body_ac_ids:
        errors.append("feature.md acceptance criteria must use AC-xxx ids")

    for marker in sorted(noncanonical_story_markers(body_text)):
        errors.append(f"feature.md uses non-canonical story marker {marker}; use US-xxx")

    if isinstance(scenarios, list):
        for item in scenarios:
            if not isinstance(item, dict):
                continue
            story_id = item.get("story_id")
            if isinstance(story_id, str) and re.fullmatch(r"US-\d{3}", story_id) and story_id not in body_story_ids:
                errors.append(f"feature scenario references undeclared story_id {story_id}")

    if re.search(r"(?mi)^###\s+AC\d+:", text) and not scenarios:
        errors.append("checklist AC is not enough; add structured scenarios")
    risk_level = meta.get("risk_level", "high")
    complexity_tier = meta.get("complexity_tier", "standard")
    rework_risk = meta.get("rework_risk", "medium")
    if rework_risk not in {"critical", "high", "medium", "low"}:
        errors.append("feature.md rework_risk must be critical|high|medium|low")

    existing_note = meta.get("existing_implementation_note")
    if is_blank_or_marker(existing_note):
        errors.append("feature.md existing_implementation_note must be explicit; use N/A — reason when not applicable")

    experience_surface = meta.get("experience_surface")
    if experience_surface not in {"user_visible", "internal_only", "mixed"}:
        errors.append("feature.md experience_surface must be user_visible|internal_only|mixed")

    intent_review = meta.get("intent_review")
    intent_required = complexity_tier in {"standard", "deep"} or risk_level in {"critical", "high"} or rework_risk in {"critical", "high"}
    if intent_required:
        if not isinstance(intent_review, dict):
            errors.append("feature.md intent_review is required for standard/deep/high/rework-high features")
        else:
            status = intent_review.get("status")
            if status not in {"confirmed", "overridden"}:
                errors.append("feature.md intent_review must be confirmed or overridden before planning can pass")
            elif status == "confirmed":
                reviewed_items = intent_review.get("reviewed_items") or []
                required_items = {"user_story", "non_goals", "key_scenarios"}
                if set(reviewed_items) < required_items:
                    errors.append("feature.md intent_review reviewed_items must cover user_story, non_goals, and key_scenarios before confirmation")
                if not intent_review.get("confirmed_by"):
                    errors.append("feature.md intent_review confirmed_by is required when status=confirmed")
                if not intent_review.get("confirmed_at"):
                    errors.append("feature.md intent_review confirmed_at is required when status=confirmed")

    split = meta.get("split_assessment")
    if isinstance(split, dict):
        triggered = split.get("triggered_conditions", [])
        triggered_count = len(triggered) if isinstance(triggered, list) else 0
        decision = split.get("decision")
        if triggered_count >= 2 and decision != "override_proceed":
            errors.append("feature.md split_assessment requires split or override when two or more conditions trigger")
        if decision == "override_proceed" and is_blank_or_marker(split.get("override_reason")):
            errors.append("feature.md split_assessment override_proceed requires non-empty override_reason")
    elif complexity_tier in {"standard", "deep"}:
        errors.append("feature.md split_assessment is required for standard/deep features")

    if getattr(args, "project_root", None):
        commit = meta.get("last_verified_commit")
        paths = implementation_paths(meta.get("implementation_paths"))
        if isinstance(commit, str) and paths:
            project_root = Path(args.project_root)
            for changed_path in changed_paths_after_commit(project_root, commit, paths):
                if changed_path.startswith("docs_freshness_unavailable:"):
                    errors.append(changed_path)
                else:
                    errors.append(f"docs_may_be_stale:{changed_path} changed after last_verified_commit")
    return errors


def check_design(args: argparse.Namespace) -> list[str]:
    feature_text = Path(args.feature).read_text(encoding="utf-8")
    design_text = Path(args.design).read_text(encoding="utf-8")
    feature_ids = scenario_ids_from_feature(feature_text)
    coverage_section = design_text
    match = re.search(r"(?is)scenario coverage|story mapping|0\.6", design_text)
    if match:
        coverage_section = design_text[match.start():]
    design_ids = scenario_ids_from_text(coverage_section)
    errors = [f"design.md missing scenario coverage for {sid}" for sid in sorted(feature_ids - design_ids)]

    strategy_rows = e2e_strategy_rows(design_text)
    for sid in sorted(feature_ids - set(strategy_rows)):
        errors.append(f"design.md missing E2E strategy row for {sid}")
    for sid, row in strategy_rows.items():
        if sid in feature_ids and not e2e_row_has_explicit_non_blackbox_reason(row):
            errors.append(f"design.md E2E strategy row for {sid} must include an explicit reason when not black-box verified")
    return errors


def overview_rows(text: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and re.fullmatch(r"T\d{3}", cells[0]):
            rows[cells[0]] = {
                "status": cells[1].lower(),
                "depends_on": cells[2],
                "type": cells[3],
                "receipt": cells[4],
            }
    return rows


def detail_statuses(text: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^\s*#{3,4}\s+(T\d{3})[:：].*$", text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start():end]
        status = re.search(r"task_readiness\**:\s*`?([a-z_]+)`?", block)
        if status:
            statuses[match.group(1)] = status.group(1).lower()
    return statuses


def check_plan(args: argparse.Namespace) -> list[str]:
    text = Path(args.tasks).read_text(encoding="utf-8")
    rows = overview_rows(text)
    details = detail_statuses(text)
    done = {task_id for task_id, row in rows.items() if row["status"] == "done"}
    errors: list[str] = []
    for task_id, row in rows.items():
        if task_id in details and details[task_id] != row["status"]:
            errors.append(f"{task_id}: overview status {row['status']} disagrees with task_readiness {details[task_id]}")
        if row["status"] == "ready":
            deps = re.findall(r"T\d{3}", row["depends_on"])
            for dep in deps:
                if dep not in done:
                    errors.append(f"{task_id}: ready task depends on non-done dependency {dep}")
        if row["type"] == "implementation" and row["receipt"] and not re.fullmatch(r"receipts\.json#T\d{3}", row["receipt"]):
            errors.append(f"{task_id}: implementation receipt must use receipts.json#Txxx")
    if ".claude/tdd-receipts" in text:
        errors.append(".claude/tdd-receipts is not a canonical feature receipt path")
    blocks = task_blocks(text)
    for task_id, row in rows.items():
        if row["status"] == "ready" and row["type"] == "implementation":
            block = blocks.get(task_id, "")
            if "test mapping" not in block.lower() and "测试映射" not in block:
                errors.append(f"{task_id}: ready implementation task missing test mapping")
            if "execution block" not in block.lower() and "Execution Block" not in block:
                errors.append(f"{task_id}: ready task missing Execution Block")

    if getattr(args, "feature", None):
        feature_text = Path(args.feature).read_text(encoding="utf-8")
        feature_ids = scenario_ids_from_feature(feature_text)
        task_ids = scenario_ids_from_text(text)
        for sid in sorted(feature_ids - task_ids):
            errors.append(f"tasks.md missing task coverage for scenario {sid}")

    if getattr(args, "design", None):
        design_text = Path(args.design).read_text(encoding="utf-8")
        for sid, row in sorted(e2e_strategy_rows(design_text).items()):
            level = e2e_requirement_level(row)
            if level is None:
                continue
            evidence = scenario_task_evidence(text, sid)
            if not evidence:
                errors.append(f"{sid}: design requires {level} black-box coverage but tasks.md has no task evidence")
                continue
            if not has_blackbox_verify_command(evidence):
                errors.append(f"{sid}: design requires {level} black-box coverage but tasks.md has no black-box verify command")
            if level == "formal_e2e" and not has_formal_e2e_command(evidence):
                errors.append(f"{sid}: design requires formal_e2e but tasks.md has no formal E2E command")

    if getattr(args, "prebuild_review", None):
        review_text = Path(args.prebuild_review).read_text(encoding="utf-8")
        if "## Spec Convergence" not in review_text:
            errors.append("prebuild-review.md missing Spec Convergence section")
        if "| Scenario | Story | Design Ref | Task IDs | Test Mapping | Status | Gap |" not in review_text:
            errors.append("prebuild-review.md missing Coverage Matrix")
    return errors


def check_root(args: argparse.Namespace) -> list[str]:
    project = Path(args.project_root)
    meta_path = project / ".bewater" / "install-meta.json"
    if not meta_path.exists():
        return ["missing .bewater/install-meta.json"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    application_root = meta.get("application_root")
    app_path = project if application_root == "." else project / str(application_root)
    root_has_product = any((project / marker).exists() for marker in ("package.json", "src", "tests"))
    app_has_product = any((app_path / marker).exists() for marker in ("package.json", "src", "tests"))
    if application_root != "." and root_has_product and not app_has_product:
        return [f"application_root={application_root!r} but product files live at project root"]

    errors: list[str] = []
    architecture_path = project / "docs" / "00-project" / "architecture.md"
    if application_root and application_root != "." and architecture_path.exists():
        architecture = architecture_path.read_text(encoding="utf-8")
        lower_architecture = architecture.lower()
        mentions_relative_root = (
            "application_root" in architecture
            and str(application_root) in architecture
            and ("相对于" in architecture or "relative to" in lower_architecture)
        )
        prefixes_app_root = bool(
            re.search(
                rf"(?m)^\s*{re.escape(str(application_root))}/(?:src|public|package\.json|tests)\b",
                architecture,
            )
        )
        has_root_style_tree = bool(re.search(r"(?m)^\s*(?:src|public|package\.json|tests)/?\b", architecture))
        if has_root_style_tree and not (mentions_relative_root or prefixes_app_root):
            errors.append(
                "docs/00-project/architecture.md directory tree ignores "
                f"application_root={application_root!r}; prefix paths with {application_root}/ "
                "or state that paths are relative to application_root"
            )
    return errors


def check_product_plan(args: argparse.Namespace) -> list[str]:
    project_root = Path(getattr(args, "project_root", ".") or ".")
    plan_path = (
        Path(args.product_plan)
        if getattr(args, "product_plan", None)
        else project_root / "docs" / "00-project" / "product-plan.md"
    )
    if not plan_path.exists():
        return ["missing docs/00-project/product-plan.md"]

    text = plan_path.read_text(encoding="utf-8")
    errors: list[str] = []

    for heading in PRODUCT_PLAN_REQUIRED_SECTIONS:
        if not markdown_section(text, heading).strip():
            errors.append(f"product-plan.md missing required section: {heading}")

    candidates = product_plan_candidate_rows(text)
    if not candidates:
        errors.append("product-plan.md missing Feature Candidate Map rows")
        return errors

    recommended = [row for row in candidates if row["status"].strip().lower() == "recommended"]
    if len(recommended) != 1:
        errors.append("product-plan.md must have exactly one recommended candidate")
    recommended_id = recommended_product_plan_candidate_id(text)
    if not recommended_id:
        errors.append("product-plan.md missing Recommended Next Feature candidate_id")
    elif len(recommended) == 1 and recommended[0]["id"] != recommended_id:
        errors.append("product-plan.md recommended candidate_id must match Feature Candidate Map")

    for row in candidates:
        cid = row["id"].strip()
        priority = row["priority"].strip()
        status = row["status"].strip()
        if priority and priority not in ALLOWED_PRODUCT_PLAN_PRIORITY:
            errors.append(f"{cid} priority must be P1|P2|P3")
        if status and status not in ALLOWED_PRODUCT_PLAN_STATUS:
            errors.append(
                f"{cid} status must be candidate|recommended|in_goal|active_feature|shipped|blocked|superseded"
            )
        if not row["mvp_role"].strip():
            errors.append(f"{cid} missing MVP role")
        if not row["observable_effect"].strip():
            errors.append(f"{cid} missing observable effect")

    if has_date_based_commitment(text):
        errors.append("product-plan.md must not contain date-based roadmap commitments")

    lower = text.lower()
    if any(marker.lower() in lower for marker in TASK_LEVEL_LEAKAGE_MARKERS):
        errors.append("product-plan.md must not contain task-level execution details")

    return errors


def add_common_flags(command: argparse.ArgumentParser) -> None:
    command.add_argument("--warn-only", action="store_true", help="Report drift without failing.")
    command.add_argument("--migrate", action="store_true", help="Print migration hints without rewriting files.")
    command.add_argument("--include-shipped", action="store_true", help="Allow callers to include shipped features.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BeWater semantic checks.")
    sub = parser.add_subparsers(dest="command", required=True)
    feature = sub.add_parser("feature")
    feature.add_argument("--feature", required=True)
    feature.add_argument("--project-root")
    add_common_flags(feature)
    design = sub.add_parser("design")
    design.add_argument("--feature", required=True)
    design.add_argument("--design", required=True)
    add_common_flags(design)
    plan = sub.add_parser("plan")
    plan.add_argument("--tasks", required=True)
    plan.add_argument("--feature")
    plan.add_argument("--design")
    plan.add_argument("--prebuild-review")
    add_common_flags(plan)
    root_cmd = sub.add_parser("root")
    root_cmd.add_argument("--project-root", required=True)
    add_common_flags(root_cmd)
    product_plan = sub.add_parser("product-plan")
    product_plan.add_argument("--project-root", default=".")
    product_plan.add_argument("--product-plan")
    add_common_flags(product_plan)

    args = parser.parse_args()
    handlers = {
        "feature": check_feature,
        "design": check_design,
        "plan": check_plan,
        "root": check_root,
        "product-plan": check_product_plan,
    }
    errors = handlers[args.command](args)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        if args.migrate:
            print("migration hint: add structured frontmatter scenarios, use receipts.json#Txxx, and align task status before rerunning", file=sys.stderr)
        if args.warn_only:
            return 0
        return 1
    print(f"bewater {args.command} check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
