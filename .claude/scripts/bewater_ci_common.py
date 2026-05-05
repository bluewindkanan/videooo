from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path


DEFAULT_RELEASE_CONFIG = {
    "version": 1,
    "release_boundary": "local",
    "adapters": [
        {
            "id": "local-record",
            "type": "local",
            "enabled": True,
            "actions": ["release_record", "commit"],
        }
    ],
}


def is_installed_project(project_root: Path) -> bool:
    return (
        (project_root / ".bewater/state.json").is_file()
        and (project_root / ".bewater/install-meta.json").is_file()
        and (project_root / ".claude/skills").is_dir()
        and (project_root / ".claude/agents").is_dir()
    )


def require_installed_project(project_root: Path) -> None:
    if is_installed_project(project_root):
        return
    raise SystemExit(
        "This command must run from an installed BeWater project with "
        ".bewater/state.json and .bewater/install-meta.json. "
        "For methodology source checks, run python3 tests/run_tests.py."
    )


def load_state(project_root: Path) -> dict:
    state_path = project_root / ".bewater" / "state.json"
    return json.loads(state_path.read_text(encoding="utf-8"))


def load_release_config(project_root: Path) -> dict:
    release_path = project_root / ".bewater" / "release.json"
    if not release_path.exists():
        return json.loads(json.dumps(DEFAULT_RELEASE_CONFIG))
    return json.loads(release_path.read_text(encoding="utf-8"))


def enabled_release_adapters(config: dict) -> list[dict]:
    adapters = config.get("adapters", [])
    if not isinstance(adapters, list):
        return []
    return [item for item in adapters if isinstance(item, dict) and item.get("enabled") is True]


def release_plan(config: dict) -> dict:
    adapters = enabled_release_adapters(config)
    will_commit = any(item.get("type") == "local" and "commit" in item.get("actions", []) for item in adapters)
    will_tag = any(item.get("type") == "local" and "tag" in item.get("actions", []) for item in adapters)
    will_push = any(item.get("type") == "git_push" for item in adapters)
    will_run_script = any(item.get("type") == "script" for item in adapters)
    requires_ack = any(
        item.get("requires_irreversible_ack") is True or item.get("type") in {"git_push", "script"}
        for item in adapters
        if item.get("type") in {"git_push", "script"}
    )
    return {
        "release_boundary": config.get("release_boundary", "local"),
        "adapters": adapters,
        "remote_effects": {
            "will_commit": will_commit,
            "will_tag": will_tag,
            "will_push": will_push,
            "will_run_script": will_run_script,
        },
        "requires_irreversible_ack": requires_ack,
    }


def project_path(project_root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def command_payload(name: str, command: list[str], result: subprocess.CompletedProcess[str]) -> dict:
    return {
        "name": name,
        "command": " ".join(shlex.quote(part) for part in command),
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def run_preflight_command(name: str, command: list[str], cwd: Path) -> dict:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    return command_payload(name, command, result)


def tasks_have_completed_implementation(tasks_path: Path) -> bool:
    if not tasks_path.exists():
        return False
    text = tasks_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and re.fullmatch(r"T\d{3}", cells[0]) and cells[1].lower() == "done" and cells[3] == "implementation":
            return True
        if re.match(r"^- \[(x|X)\] T\d{3}", line.strip()):
            return True
    return False


def semantic_next_action(name: str) -> str:
    return {
        "root": "bewater-init",
        "feature": "bewater-goal",
        "design": "bewater-plan",
        "plan": "bewater-plan",
        "receipts": "bewater-build",
    }.get(name, "bewater-plan")


def semantic_preflight_errors(results: list[dict]) -> list[str]:
    errors: list[str] = []
    for result in results:
        if result["exit_code"] == 0:
            continue
        detail = result["stderr"] or result["stdout"] or f"{result['name']} failed"
        for line in detail.splitlines():
            if line.strip():
                errors.append(line.strip())
    return errors


def recommended_action_for_semantic_failures(results: list[dict]) -> str:
    for result in results:
        if result["exit_code"] != 0:
            return semantic_next_action(str(result["name"]))
    return "none"


def run_semantic_preflights(project_root: Path, state: dict, script_dir: Path | None = None) -> list[dict]:
    script_dir = script_dir or Path(__file__).resolve().parent
    results: list[dict] = []

    checker = script_dir / "bewater-check.py"
    receipt_checker = script_dir / "check-tdd-receipts.py"

    results.append(
        run_preflight_command(
            "root",
            ["python3", str(checker), "root", "--project-root", str(project_root)],
            project_root,
        )
    )

    artifacts = state.get("artifacts", {}) if isinstance(state.get("artifacts"), dict) else {}
    feature_path = project_path(project_root, artifacts.get("feature_path"))
    design_path = project_path(project_root, artifacts.get("design_path"))
    tasks_path = project_path(project_root, artifacts.get("tasks_path"))
    prebuild_review_path = project_path(project_root, artifacts.get("prebuild_review_path"))

    if feature_path is not None:
        results.append(
            run_preflight_command(
                "feature",
                [
                    "python3",
                    str(checker),
                    "feature",
                    "--feature",
                    str(feature_path),
                    "--project-root",
                    str(project_root),
                ],
                project_root,
            )
        )

    if feature_path is not None and design_path is not None:
        results.append(
            run_preflight_command(
                "design",
                [
                    "python3",
                    str(checker),
                    "design",
                    "--feature",
                    str(feature_path),
                    "--design",
                    str(design_path),
                ],
                project_root,
            )
        )

    if tasks_path is not None:
        command = ["python3", str(checker), "plan", "--tasks", str(tasks_path)]
        if feature_path is not None:
            command.extend(["--feature", str(feature_path)])
        if design_path is not None:
            command.extend(["--design", str(design_path)])
        if prebuild_review_path is not None:
            command.extend(["--prebuild-review", str(prebuild_review_path)])
        results.append(run_preflight_command("plan", command, project_root))

        receipts_path = tasks_path.parent / "receipts.json"
        if receipts_path.exists() or tasks_have_completed_implementation(tasks_path):
            results.append(
                run_preflight_command(
                    "receipts",
                    [
                        "python3",
                        str(receipt_checker),
                        "--tasks",
                        str(tasks_path),
                        "--receipts",
                        str(receipts_path),
                    ],
                    project_root,
                )
            )

    return results


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return int(payload.get("exit_code", 0))
