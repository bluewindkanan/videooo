# Pre-Build Review
feature: [feature-id]
review_status: passed|failed|blocked
gate_name: prebuild_review_gate
recommended_gate_status: passed|failed|blocked
input_digest: [sha256-aggregate]
input_refs:
  - docs/01-features/{feature}/feature.md
  - docs/01-features/{feature}/design.md
  - docs/01-features/{feature}/tasks.md
input_digests:
  docs/01-features/{feature}/feature.md: [sha256]
  docs/01-features/{feature}/design.md: [sha256]
  docs/01-features/{feature}/tasks.md: [sha256]
evidence_refs: []

## Reviewed Inputs
- `docs/01-features/{feature}/feature.md`
- `docs/01-features/{feature}/design.md`
- `docs/01-features/{feature}/tasks.md`

## Spec Convergence

- feature scenarios have design coverage: pass|fail
- feature scenarios have task coverage: pass|fail
- every implementation task maps to scenario or AC: pass|fail
- every ready task has test mapping: pass|fail
- no task expands beyond feature scope without explicit rationale: pass|fail
- split assessment is acceptable or overridden: pass|fail
- required intent confirmation is present: pass|fail
- user-visible scenarios define entry points and discovery path: pass|fail
- user-visible scenarios have discoverability task coverage: pass|fail

### Convergence Findings

| Check | Status | Source | Resolution |
|-------|--------|--------|------------|
| intent confirmation | pass|fail | feature.md | N/A — covered |
| split assessment | pass|fail | feature.md | N/A — covered |
| scenario to design | pass|fail | feature.md + design.md | N/A — covered |
| scenario to tasks | pass|fail | feature.md + tasks.md | N/A — covered |
| discoverability coverage | pass|fail | feature.md + design.md + tasks.md | N/A — covered |

## Coverage Matrix
| Scenario | Story | Design Ref | Task IDs | Test Mapping | Status | Gap |
|----------|-------|------------|----------|--------------|--------|-----|
| S-001 | US-001 | design.md §0.6 | T201 | unit + e2e | pass | N/A — covered |

## E2E Asset Readiness

> `static_verify` rows do not satisfy user-visible scenario coverage by themselves. `blackbox_smoke` requires a concrete boundary command such as `curl`; `formal_e2e` requires a durable E2E asset such as Playwright. `agent-browser is supplemental` and appears as `exploratory_browser` evidence only.

| Scenario | Required level | Test asset task | Spec or smoke path | Driver | RED command | Verify command | Status |
|----------|----------------|-----------------|--------------------|--------|-------------|----------------|--------|
| S-001 | static_verify / blackbox_smoke / formal_e2e | T201 | `tests/blackbox/example.sh` or `e2e/flows/example.spec.ts` | curl / Playwright | `curl -fsS ...` | `npx playwright test ... --grep "@S-001"` | pass/fail |

## Dependency and Reuse Findings
- dependency order: pass|fail
- forward dependency check: pass|fail
- callsites / reuse checklist completeness: pass|fail
- implementation_mode routing: pass|fail

## Readiness Findings
- no scenario drift: pass|fail
- no underbuild: pass|fail
- no overbuild: pass|fail
- no fake-ready task: pass|fail
- every ready task has complete `Execution Block`: pass|fail
- risk level matches verification depth: pass|fail

## Findings by Severity
### Blockers
- [ ] [source ref] [issue] [required resolution]

### Concerns
- [ ] [source ref] [issue] [recommended resolution]

### Notes
- [ ] [source ref] [observation]

## Gate Recommendation
- recommended_gate_status: passed|failed|blocked
- recommended_next_action: `/bewater-build | /bewater-plan | /bewater-goal`

## Gate Rules
- passed: next dispatchable ready set can be implemented without planner invention
- failed: planner-owned omission, coverage gap, or fake-ready task
- blocked: product/design decision is missing or contradictory
