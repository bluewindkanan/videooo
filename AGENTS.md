# AGENTS.md (BeWater + Codex Compatibility)

This repository uses **BeWater**. In Codex, treat **`CLAUDE.md`** and **`WORKFLOW.md`** as the method authorities.

## Canonical Runtime (Do Not Fork)

- **Claude Code runtime remains canonical.** Do not re-implement the lifecycle in Codex.
- Read `.bewater/state.json` before acting.
- Follow `current_state` and `next_command`.

## Public Lifecycle (SSOT)

Use the public chain as described in `WORKFLOW.md`:

`/bewater-goal -> /bewater-plan -> /bewater-build -> /bewater-validate -> /bewater-ship`

## Evidence Artifacts (Required)

For the active feature slice under `docs/01-features/<id-name>/`, keep/update:

- `feature.md`
- `design.md`
- `tasks.md`
- `review-note.md`
- `validation-report.md`
- `receipts.json` (TDD receipts where applicable)

## Mandatory Checks (Run Before Claiming "Done")

1) Semantic contract check:

`python3 .claude/scripts/bewater-check.py`

2) TDD receipts integrity (when tasks require receipts):

`python3 .claude/scripts/check-tdd-receipts.py --tasks docs/01-features/<id-name>/tasks.md --receipts docs/01-features/<id-name>/receipts.json`

3) Ship precheck evaluation (before ship precheck / release):

`python3 .claude/scripts/bewater-gate-evaluate.py --project-root . --gate ship_precheck_gate`

## Release Safety

- Never perform irreversible release actions without explicit user confirmation.
- Never ship without validate evidence.
- Do not “shortcut” by inventing new commands, new gates, or new state machines.

