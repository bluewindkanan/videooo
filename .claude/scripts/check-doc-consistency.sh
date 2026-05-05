#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

exit_code=0
set +e
python3 - "$ROOT_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
exit_code = 0
source_mode = (root / "install.sh").exists()
template_root = root / "templates" if source_mode else root / ".bewater/templates"

managed_locations = [
    "WORKFLOW.md",
    "README.md",
    "CLAUDE.md",
    "install.sh",
    ".claude/agents",
    ".claude/skills",
    ".claude/scripts",
    "templates/core",
    "templates/01-features/validation-report.md",
    "templates/guides/for-users",
    "templates/guides/for-developers",
    ".bewater/templates/core",
    ".bewater/templates/01-features/validation-report.md",
    ".bewater/templates/guides/for-users",
    ".bewater/templates/guides/for-developers",
]


def collect_managed_files():
    files = []
    for relative in managed_locations:
        target = root / relative
        if not target.exists():
            continue
        if target.is_file():
            files.append(target)
            continue
        for path in target.rglob("*"):
            if path.is_file():
                files.append(path)
    return files


def iter_text_files():
    for path in collect_managed_files():
        if path.name == "check-doc-consistency.sh":
            continue
        if path.suffix.lower() not in {".md", ".sh", ".json", ".yaml", ".yml"}:
            continue
        yield path


def print_section(title):
    print(f"\n== {title} ==")


def report_matches(title, matches):
    global exit_code
    print_section(title)
    if matches:
        print(f"FAIL: {title}")
        for item in matches:
            print(item)
        exit_code = 1
    else:
        print(f"OK: {title}")


def skill_inventory():
    return sorted(path.parent.name for path in (root / ".claude/skills").glob("*/SKILL.md"))


def agent_inventory():
    return sorted(path.name for path in (root / ".claude/agents").glob("*.md"))


old_path_re = re.compile(r"docs/0-intent|docs/1-constraints|docs/2-execution|docs/3-validation|docs/4-learning|docs/02-features")
old_cmd_re = re.compile(r"/bewater\.[a-z-]+")
legacy_layout_re = re.compile(r"(?<!\.claude/)agents/|(?<!\.claude/)skills/")
drift_term_re = re.compile(
    r"ready-to-ship|review_report_path|跳过 plan 和 validate"
)
forbidden_existing_cmd_re = re.compile(r"/bewater-catchup")
required_existing_mode_re = re.compile(r"implementation_mode|existing implementation|已有实现")
legacy_validate_path_re = re.compile(
    r"goal -> plan -> build -> ship|goal → plan → build → ship|internal validate -> ship|公开前置命令：无"
)
retired_flow_command_re = re.compile(r"/bewater-flow")
link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
old_ship_split_flag_re = re.compile(r"/bewater-ship(?:\s+\d+)?\s+--(?:precheck|release)(?!-only)")

# 1) 旧路径检查
old_path_hits = []
for file_path in iter_text_files():
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if old_path_re.search(line):
            old_path_hits.append(f"{file_path.relative_to(root)}:{lineno}:{line.strip()}")
report_matches("旧路径残留检测", old_path_hits)

# 2) 旧命令写法检查
old_cmd_hits = []
for file_path in iter_text_files():
    if file_path.suffix.lower() not in {".md", ".sh", ".yaml", ".yml"}:
        continue
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if old_cmd_re.search(line):
            old_cmd_hits.append(f"{file_path.relative_to(root)}:{lineno}:{line.strip()}")
report_matches("旧命令写法检测", old_cmd_hits)

# 3) 旧布局路径检查
legacy_layout_hits = []
for file_path in iter_text_files():
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if legacy_layout_re.search(line):
            legacy_layout_hits.append(f"{file_path.relative_to(root)}:{lineno}:{line.strip()}")
report_matches("旧布局路径检测", legacy_layout_hits)

# 4) 新漂移术语检查
drift_term_hits = []
for file_path in iter_text_files():
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if drift_term_re.search(line):
            drift_term_hits.append(f"{file_path.relative_to(root)}:{lineno}:{line.strip()}")
report_matches("主契约漂移术语检测", drift_term_hits)

# 4a) 新公共面必备 marker
print_section("vNext Public Surface Marker 检测")
required_public_markers = [
    "/bewater-auto",
    "/bewater-next",
    "/bewater-ship",
]
public_surface_targets = [
    [root / "README.md"],
    [
        root / "templates/guides/for-users/getting-started.md",
        root / ".bewater/templates/guides/for-users/getting-started.md",
    ],
]
public_surface_errors = []
for target_group in public_surface_targets:
    target = next((candidate for candidate in target_group if candidate.exists()), None)
    if target is None:
        public_surface_errors.append(f"{target_group[0].relative_to(root)}: missing file")
        continue
    content = target.read_text(encoding="utf-8", errors="ignore")
    for marker in required_public_markers:
        if marker not in content:
            public_surface_errors.append(f"{target.relative_to(root)}: missing marker {marker}")

if public_surface_errors:
    print("FAIL: vNext Public Surface Marker 检测")
    for item in public_surface_errors:
        print(item)
    exit_code = 1
else:
    print("OK: vNext Public Surface Marker 检测")

# 4a.1) runtime inventory consistency
print_section("Runtime inventory consistency")
inventory_errors = []
skills = skill_inventory()
agents = agent_inventory()
readme = (root / "README.md").read_text(encoding="utf-8", errors="ignore")
if len(skills) != 20:
    inventory_errors.append(f"expected 20 skills, found {len(skills)}")
if len(agents) != 8:
    inventory_errors.append(f"expected 8 agents, found {len(agents)}")
for marker in ["20 skills", "8 agents", "14 BeWater lifecycle/utility/internal skills", "6 capability-pack skills"]:
    if marker not in readme and marker.replace("skills", "Skill") not in readme:
        inventory_errors.append(f"README.md missing inventory marker {marker}")
for marker in ["product-framing", "planning-readiness", "review-pack", "tdd-implement", "validation-pack", "evidence-aggregate"]:
    if marker not in readme:
        inventory_errors.append(f"README.md missing capability-pack marker {marker}")
if inventory_errors:
    print("FAIL: Runtime inventory consistency")
    for item in inventory_errors:
        print(item)
    exit_code = 1
else:
    print("OK: Runtime inventory consistency")

# 4b) execution contract markers
print_section("Execution Contract Markers")
execution_contract_errors = []
tasks_template_candidates = [
    root / "templates/01-features/tasks.md",
    root / ".bewater/templates/01-features/tasks.md",
]
tasks_template = next((path for path in tasks_template_candidates if path.exists()), None)
if tasks_template is None:
    execution_contract_errors.append("templates/01-features/tasks.md: missing file")
else:
    tasks_text = tasks_template.read_text(encoding="utf-8", errors="ignore")
    for marker in ("Delivery Map", "Execution Block", "task_readiness:"):
        if marker not in tasks_text:
            execution_contract_errors.append(f"{tasks_template.relative_to(root)}: missing {marker}")

if execution_contract_errors:
    print("FAIL: Execution Contract Markers")
    for item in execution_contract_errors:
        print(item)
    exit_code = 1
else:
    print("OK: Execution Contract Markers")

# 4b.1) runtime hardening markers
print_section("Runtime Hardening Markers")
runtime_hardening_errors = []
runtime_hardening_markers = [
    "bewater-check.py",
    "receipts.json",
    "Semantic Preflight Matrix",
    "extension",
]
if source_mode:
    runtime_hardening_targets = [
        root / "README.md",
        root / "WORKFLOW.md",
        root / "docs/reference/runtime-contracts.md",
        root / "docs/reference/semantic-gates.md",
    ]
    for target in runtime_hardening_targets:
        if not target.exists():
            runtime_hardening_errors.append(f"{target.relative_to(root)}: missing file")
            continue
        target_text = target.read_text(encoding="utf-8", errors="ignore")
        for marker in runtime_hardening_markers:
            if marker not in target_text:
                runtime_hardening_errors.append(f"{target.relative_to(root)}: missing marker {marker}")

if runtime_hardening_errors:
    print("FAIL: Runtime Hardening Markers")
    for item in runtime_hardening_errors:
        print(item)
    exit_code = 1
else:
    print("OK: Runtime Hardening Markers")

# 4c) installable template purity
print_section("Template purity")
template_errors = []
backlog_path = template_root / "02-learning/methodology-backlog.json"
if backlog_path.exists():
    try:
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
    except Exception as exc:
        template_errors.append(f"{backlog_path.relative_to(root)}: invalid JSON {exc}")
    else:
        methodology_backlog_empty = backlog.get("items") == []
        if not methodology_backlog_empty:
            template_errors.append("templates/02-learning/methodology-backlog.json: items must be empty in installable template")
        if backlog.get("allowed_statuses") != ["open", "accepted", "rejected", "planned", "done"]:
            template_errors.append(f"{backlog_path.relative_to(root)}: allowed_statuses drift")
else:
    template_errors.append(f"{backlog_path.relative_to(root)}: missing")

for required in ["core/state.md", "core/state-template.json"]:
    required_path = template_root / required
    if not required_path.exists():
        template_errors.append(f"{required_path.relative_to(root)}: missing")
old_state_path = template_root / "core/state.json"
if old_state_path.exists():
    template_errors.append(f"{old_state_path.relative_to(root)}: remove Markdown file with JSON suffix")

tasks_path = template_root / "01-features/tasks.md"
if tasks_path.exists():
    tasks_text = tasks_path.read_text(encoding="utf-8", errors="ignore")
    for marker in [
        "Harden execution-contract vocabulary",
        "T010 Harden execution-contract vocabulary",
        "T101 Wire the next dispatchable ready task",
        "tests/test_content.py",
    ]:
        if marker in tasks_text:
            template_errors.append(f"{tasks_path.relative_to(root)}: contains BeWater-specific active sample {marker}")

if template_errors:
    print("FAIL: Template purity")
    for item in template_errors:
        print(item)
    exit_code = 1
else:
    print("OK: Template purity")

# 5) 禁止暴露 catchup 命令
forbidden_existing_cmd_hits = []
for file_path in iter_text_files():
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if forbidden_existing_cmd_re.search(line):
            forbidden_existing_cmd_hits.append(f"{file_path.relative_to(root)}:{lineno}:{line.strip()}")
report_matches("禁止暴露 catchup 命令", forbidden_existing_cmd_hits)

# 5a) 禁止残留旧的无公开 validate 链路
legacy_validate_hits = []
for file_path in iter_text_files():
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if legacy_validate_path_re.search(line):
            legacy_validate_hits.append(f"{file_path.relative_to(root)}:{lineno}:{line.strip()}")
report_matches("Legacy validate path drift", legacy_validate_hits)

# 5a.1) current ship modes only
old_ship_hits = []
ship_mode_required_hits = []
automatic_local_ship_marker = "automatic local ship"
for file_path in iter_text_files():
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if old_ship_split_flag_re.search(line):
            old_ship_hits.append(f"{file_path.relative_to(root)}:{lineno}:{line.strip()}")
    if file_path.name == "README.md" and "--precheck-only" in text:
        ship_mode_required_hits.append(file_path.relative_to(root).as_posix())
    if source_mode and file_path.name == "install.sh" and "--precheck-only" in text:
        ship_mode_required_hits.append(file_path.relative_to(root).as_posix())
report_matches("Old ship split flag drift", old_ship_hits)
required_ship_marker_count = 2 if source_mode else 1
if len(set(ship_mode_required_hits)) < required_ship_marker_count:
    required_target = "README.md and install.sh" if source_mode else "README.md"
    report_matches("Current ship mode markers", [f"{required_target} must mention --precheck-only"])
else:
    report_matches("Current ship mode markers", [])

# 5b) 禁止继续暴露已删除的 bewater-flow 命令
retired_flow_hits = []
for file_path in iter_text_files():
    relative = file_path.relative_to(root).as_posix()
    if relative.startswith("docs/superpowers/"):
        continue
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if retired_flow_command_re.search(line):
            retired_flow_hits.append(f"{file_path.relative_to(root)}:{lineno}:{line.strip()}")
report_matches("Retired bewater-flow command drift", retired_flow_hits)

# 6) existing implementation 契约存在性检测
existing_mode_hits = []
required_targets = [
    root / "README.md",
    root / "WORKFLOW.md",
    root / "CLAUDE.md",
    root / ".claude/skills",
    root / "templates/core",
    root / "templates/01-features",
    root / "templates/guides/for-users",
    root / "templates/guides/for-developers",
]
for target in required_targets:
    if not target.exists():
        continue
    paths = [target] if target.is_file() else [p for p in target.rglob("*") if p.is_file()]
    for file_path in paths:
        if file_path.suffix.lower() not in {".md", ".sh", ".json", ".yaml", ".yml"}:
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if required_existing_mode_re.search(text):
            existing_mode_hits.append(file_path.relative_to(root).as_posix())
            break
if existing_mode_hits:
    print_section("existing implementation 契约检测")
    print("OK: existing implementation 契约检测")
else:
    report_matches("existing implementation 契约检测", ["missing implementation_mode/existing implementation markers"])

# 7) README 安装面契约检测
print_section("README 安装面契约检测")
readme_install_errors = []

consistency_content = (root / ".claude/scripts/check-doc-consistency.sh").read_text(encoding="utf-8", errors="ignore")
if "readme_doc" not in consistency_content and "README.bewater.md" not in consistency_content:
    readme_install_errors.append("check-doc-consistency.sh: missing README install-surface drift marker")

if (root / "install.sh").exists():
    install_content = (root / "install.sh").read_text(encoding="utf-8", errors="ignore")
    readme_content = (root / "README.md").read_text(encoding="utf-8", errors="ignore")
    workflow_content = (root / "WORKFLOW.md").read_text(encoding="utf-8", errors="ignore")

    if "copy_readme_doc" not in install_content:
        readme_install_errors.append("install.sh: missing copy_readme_doc")
    if "readme_doc" not in install_content:
        readme_install_errors.append("install.sh: missing readme_doc metadata")
    if ".bewater/README.bewater.md" not in install_content:
        readme_install_errors.append("install.sh: missing README fallback path")
    if "README.bewater.md" not in readme_content:
        readme_install_errors.append("README.md: missing README fallback behavior documentation")
    if "README.bewater.md" not in workflow_content:
        readme_install_errors.append("WORKFLOW.md: missing README fallback behavior documentation")
else:
    meta_path = root / ".bewater/install-meta.json"
    if not meta_path.exists():
        readme_install_errors.append(".bewater/install-meta.json: missing install metadata")
    else:
        try:
            meta_data = json.loads(meta_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            readme_install_errors.append(".bewater/install-meta.json: invalid JSON")
            meta_data = {}

        for key in ("readme_doc", "application_root", "app_readme_doc"):
            value = str(meta_data.get(key, "")).strip()
            if not value:
                readme_install_errors.append(f".bewater/install-meta.json: missing {key}")
                continue
            resolved = root / value
            if not resolved.exists():
                readme_install_errors.append(
                    f".bewater/install-meta.json: {key} path not found -> {value}"
                )

if readme_install_errors:
    print("FAIL: README 安装面契约检测")
    for item in readme_install_errors:
        print(item)
    exit_code = 1
else:
    print("OK: README 安装面契约检测")

# 8) Markdown 链接有效性
print_section("Markdown 链接有效性检测")
checked_links = 0
missing_links = []
for md in (path for path in iter_text_files() if path.suffix.lower() == ".md"):
    text = md.read_text(encoding="utf-8", errors="ignore")
    for link in link_re.findall(text):
        if "://" in link or link.startswith("#") or link.startswith("mailto:"):
            continue
        target = link.split("#")[0].strip()
        if not target:
            continue
        if target.startswith("/") and not target.startswith("/Users/"):
            continue
        resolved = Path(target) if target.startswith("/") else (md.parent / target).resolve()
        checked_links += 1
        if not resolved.exists():
            missing_links.append(f"{md.relative_to(root)} :: {link}")

print(f"checked_links={checked_links}")
if missing_links:
    print(f"missing_links={len(missing_links)}")
    for item in missing_links:
        print(item)
    exit_code = 1
else:
    print("missing_links=0")
    print("OK: Markdown 链接有效性检测")

print_section("结果")
if exit_code == 0:
    print("All checks passed.")
else:
    print("Consistency check failed.")

sys.exit(exit_code)
PY
exit_code=$?
set -e

if [ -x "$ROOT_DIR/.claude/scripts/check-template-purity.py" ]; then
    python3 "$ROOT_DIR/.claude/scripts/check-template-purity.py" --root "$ROOT_DIR" || exit_code=1
fi

exit "$exit_code"
