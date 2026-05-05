---
name: bewater-auto
description: Feature automation entry that runs BeWater delivery until shippable or blocked
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
user-invocable: true
context: feature args + state.json + gates + flow routing
effort: medium
---

# BeWater Auto

Feature automation entry for turning a user feature request into a shippable BeWater feature.

## Responsibilities
- inspect current state and gates
- run the dispatcher loop until a hard stop is reached
- pass args to `/bewater-goal {args}` when starting from `initialized`
- choose the next allowed flow from `state.next_command` or the route table
- continue lifecycle execution without asking for workflow confirmation
- stop at blockers, clarification points, host permission prompts, or release boundaries
- treat goal clarification and release decision as human gates, not workflow confirmation noise

## PM-facing Automation Summary

When reporting progress or a stop condition, show product-facing language first:

- Product decision: what was clarified, planned, validated, or blocked.
- Evidence links: `feature.md`, `tasks.md`, `review-note.md`, `validation-report.md`, and release evidence when available.
- Release choices: default automation may complete automatic local ship (release record + local commit); remote effects require explicit user confirmation and irreversible acknowledgement.

The only default human gates are goal confirmation and release decision. internal gate names are secondary; include `review_gate` and `ship_precheck_gate` only as audit details after the plain-language summary.

Use these boundary labels consistently:

- Goal Brief
- Build Plan
- Validation Dossier
- Release Decision

## Input Args
- Plain-language args are the initial feature description for `/bewater-goal {args}`.
- Numeric args select or resume a feature id.
- Args do not replace goal interaction; `/bewater-goal` must still clarify and confirm ambiguous product intent before writing `feature.md`.

## Targets
- default target: run goal -> plan -> build -> validate -> `/bewater-ship`, completing automatic local ship when gates pass. Local ship means release record + local commit only.
- `--until validate`: stop after fresh `validation_outcome`.
- `--precheck-only`: run through `/bewater-ship --precheck-only` and stop without local commit, tag, push, deploy, or script adapters.
- `--with-release`: may provide explicit release intent for configured remote effects. Remote adapters still require irreversible acknowledgement.

## Dispatcher Loop
1. Read `.bewater/state.json`.
2. Check gate freshness, blockers, `runtime.validation_outcome`, and `runtime.retry_counters`.
3. Select the next action from `next_command` when it is valid for the current state, target, gate freshness, `validation_outcome`, and release safety rules.
4. If `next_command` is missing, stale, or inconsistent, use the route table below.
5. Execute the selected BeWater lifecycle skill.
6. Re-read `.bewater/state.json`.
7. Continue until a hard stop occurs.

This is an autonomous runner. It must not ask the user "should I continue?" between safe BeWater lifecycle steps. This is the no workflow confirmation rule.

## Route Table
| Current condition | Next automatic route |
|-------------------|----------------------|
| `uninitialized` | stop; recommend `/bewater-init` |
| `initialized` | `/bewater-goal {args}` |
| `specified` | `/bewater-plan` |
| `planned` + `implementation_mode=greenfield` | `/bewater-build` |
| `planned` + `implementation_mode=extension` | `/bewater-build` |
| `planned` + `implementation_mode=existing_partial` | `/bewater-build` |
| `planned` + `implementation_mode=existing_complete` | `/bewater-validate` |
| `building` + no fresh `validation_outcome` | `/bewater-validate` |
| `building` + `validation_outcome.release_decision=go` + `validation_outcome.classification=ready_for_precheck` + default target | `/bewater-ship` for automatic local ship |
| `building` + `validation_outcome.release_decision=go` + `validation_outcome.classification=ready_for_precheck` + `--until validate` | stop; report validation result |
| `building` + `validation_outcome.release_decision=go` + `validation_outcome.classification=ready_for_precheck` + `--precheck-only` | `/bewater-ship --precheck-only` |
| `building` + `validation_outcome.release_decision=go` + `validation_outcome.classification=ready_for_precheck` + `--with-release` | `/bewater-ship` with explicit release intent for remote effects |
| `building` + `validation_outcome.release_decision=no-go` + `validation_outcome.classification=implementation_gap` | `/bewater-build` unless repeat blocker limit is hit |
| `building` + `validation_outcome.release_decision=no-go` + `validation_outcome.classification=spec_package_drift` | `/bewater-plan` |
| `building` + `validation_outcome.release_decision=no-go` + `validation_outcome.classification=goal_scope_contradiction` | stop; report blockers and recommend `/bewater-goal` |
| `building` + repeated unchanged blocking `validation_outcome` | stop; report blockers |
| `shipped` | stop; recommend `/bewater-learn` or `/bewater-goal` |

## Hard Stops
- user/product clarification is required
- goal clarification or explicit goal confirmation is required before `feature.md` can be treated as confirmed
- any required gate is `failed` or `blocked`
- a host/tool permission prompt requires user approval
- the same blocking `validation_outcome` repeats against unchanged inputs more than once
- `evidence_incomplete_or_stale` has already used its one automatic refresh retry
- remote push/deploy/script effects would occur without explicit release intent and irreversible acknowledgement

Hard-stop reports must include `Product decision`, `Evidence links`, and `Recommended next action` before listing technical gate details.

## Safety Rules
- never perform remote effects without explicit release intent and irreversible acknowledgement
- default automation may perform automatic local ship only after fresh validation evidence, `release_decision=go`, `classification=ready_for_precheck`, and ship precheck go
- automatic local ship is limited to release record + local commit from the local adapter; it must not push, deploy, publish, or run script adapters
- `--precheck-only` must not execute local commit, tag, push, deploy, or script adapters
- stop if the same blocking `validation_outcome` repeats against unchanged inputs more than once
- allow only one automatic retry for `evidence_incomplete_or_stale`
- if `--with-release` is present, release intent is explicit, and `/bewater-ship` returns `go`, the ship flow may complete configured remote effects only after irreversible acknowledgement
- treat stale `next_command=/bewater-ship` as inconsistent when validation evidence is missing or stale

Semantic preflights are defined in `.claude/skills/SHARED_STATE_CONTRACT.md` under "Semantic Preflight Matrix"; run the relevant check before writing a passed gate or advancing state.
