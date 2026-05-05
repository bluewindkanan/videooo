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

Semantic preflights are defined in `.claude/skills/SHARED_STATE_CONTRACT.md` under "Semantic Preflight Matrix"; run the relevant check before writing a passed gate or advancing state.
