# Feature Definition Review
feature: [feature-id]
review_status: passed|failed|blocked
gate_name: feature_review_gate
recommended_gate_status: passed|failed|blocked
input_digest: [sha256]
input_refs:
  - docs/01-features/{feature}/feature.md
input_digests:
  docs/01-features/{feature}/feature.md: [sha256]
evidence_refs: []

## Reviewed Input
- `docs/01-features/{feature}/feature.md`

## Source Contract Checks

| Check | Status | Source | Resolution |
|-------|--------|--------|------------|
| frontmatter scenarios exist | pass|fail | feature.md | N/A — covered |
| scenario IDs use S-xxx | pass|fail | feature.md | N/A — covered |
| story IDs use US-xxx | pass|fail | feature.md | N/A — covered |
| body declares matching US stories | pass|fail | feature.md | N/A — covered |
| scenarios use Given/When/Then | pass|fail | feature.md | N/A — covered |
| acceptance criteria use AC-xxx | pass|fail | feature.md | N/A — covered |
| scenarios map to AC refs | pass|fail | feature.md | N/A — covered |
| scope and non-goals are explicit | pass|fail | feature.md | N/A — covered |
| intent review status is valid | pass|fail | feature.md | N/A — covered |
| split assessment is valid | pass|fail | feature.md | N/A — covered |

## Source Inventory

| Story | Priority | Scenarios | Acceptance Criteria | Status |
|-------|----------|-----------|---------------------|--------|
| US-001 | P1 | S-001 | AC-001 | pass|fail |

## Findings by Severity

### Blockers
- [ ] [source ref] [issue] [required resolution]

### Concerns
- [ ] [source ref] [issue] [recommended resolution]

### Notes
- [ ] [source ref] [observation]

## Gate Recommendation
- recommended_gate_status: passed|failed|blocked
- recommended_next_action: `/bewater-architect | revise feature.md | clarify product intent`
