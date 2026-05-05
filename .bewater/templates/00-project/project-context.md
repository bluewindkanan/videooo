# Project Context

> AI Implementation Context. This file is a compact implementation guide for agents.
> It is not a gate artifact, not a delivery state source, and not a replacement for `.bewater/state.json`.

## Authority

- Lifecycle state, gates, and next command: `.bewater/state.json`
- Current implementation rules: this file plus `architecture.md` and `constitution.md`
- Feature delivery history: `docs/01-features/*`
- Current behavior evidence: code, tests, git history, and validation reports

When this file conflicts with code evidence, treat this file as stale and report the mismatch.

## Tech Stack

| Area | Choice | Notes |
|------|--------|-------|
| Runtime | [Node/Python/Go/etc.] | [version or N/A] |
| Frontend | [framework or N/A] | [router/state/ui notes] |
| Backend | [framework or N/A] | [API/service notes] |
| Database | [database or N/A] | [migration notes] |
| Test Runner | [tooling] | [unit/integration/e2e notes] |

## Key Paths

| Purpose | Path | Notes |
|---------|------|-------|
| Application root | [path] | Must match `.bewater/install-meta.json` |
| Source code | [path] | [module conventions] |
| Tests | [path] | [test naming conventions] |
| E2E tests | [path or N/A] | [runtime setup] |
| Build output | [path] | [ignored/generated] |

## Implementation Conventions

- [Rule 1]
- [Rule 2]
- [Rule 3]

## Test Commands

| Scope | Command | Expected use |
|-------|---------|--------------|
| Unit | `[command]` | Before marking implementation tasks done |
| Integration | `[command or N/A]` | When API/storage behavior changes |
| E2E | `[command or N/A]` | For user-visible flows |
| Full verification | `[command]` | Before ship/precheck |

## Current Architecture Rules

- [Architecture constraint 1]
- [Architecture constraint 2]
- [Architecture constraint 3]

## Known Drift

> Use this section for areas where feature docs may be stale or implementation changed outside BeWater.

| Area | Status | Evidence | Recommended action |
|------|--------|----------|--------------------|
| N/A | no known drift | N/A | N/A |

## Agent Notes

1. Read this file before loading large feature docs.
2. Treat feature docs as historical delivery claims unless freshness evidence is current.
3. When editing code under stale areas, inspect current code and tests before relying on old specs.
4. Record new drift in `validation-report.md` and refresh this file after ship.
