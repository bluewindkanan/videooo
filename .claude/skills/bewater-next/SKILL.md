---
name: bewater-next
description: Read-only advisor that recommends the next public BeWater action
allowed-tools: [Read, Glob, Grep, Bash]
user-invocable: true
context: state.json + gate freshness + artifact completeness
effort: small
---

# BeWater Next

## Output
- recommended public skill
- rationale
- blocking gates
- stale gates
- missing artifacts
- whether human approval is required

## Rule
- read-only, never mutates lifecycle state
- Before proposing new methodology expansion work, read `docs/02-learning/methodology-backlog.json` if it exists. Surface open `must` methodology backlog items first and recommend addressing them before lower-priority expansion work.
- When `docs/02-learning/methodology-backlog.json` has open `must` items, surface them before recommending expansion work.
- Treat methodology backlog statuses as maintainer-owned states: `open`, `accepted`, `rejected`, `planned`, and `done`. Prefer accepted or planned `must` items over new expansion proposals.

## Product Plan Routing

When the project is `initialized` or no active feature should be continued, read `docs/00-project/product-plan.md` before asking the user to invent a feature.

`/bewater-next` remains read-only. It must not mutate `product-plan.md`, lifecycle state, or feature docs.

Recommendation order:

1. Continue an active lifecycle feature when state/gates require it.
2. Surface blocking or stale gates.
3. Surface open `must` methodology backlog items when present.
4. If no active feature blocks progress, read `product-plan.md` and recommend the single candidate with `status: recommended`.
5. If product-plan is missing, ambiguous, or blocked, recommend repairing product-plan before `/bewater-goal`.

Product-plan output must include:

- recommended public skill, usually `/bewater-goal PC-001`
- candidate ID and title
- MVP-first rationale
- observable effect
- feedback value
- whether human confirmation is required
- blocking planning issues if no candidate can be recommended

Semantic preflights are defined in `.claude/skills/SHARED_STATE_CONTRACT.md` under "Semantic Preflight Matrix"; run the relevant check before writing a passed gate or advancing state.
