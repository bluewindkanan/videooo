---
name: review-pack
description: Shared review methods for foundation review, spec-package review, compliance review, and regression-risk checks
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
user-invocable: false
context: plan-flow and build-flow review methods
effort: medium
---

# Review Pack

## Methods
- foundation-review
- feature-definition-review
- spec-package-review
- spec-compliance-review
- regression-risk-check

## Foundation Review Method
Use for `docs/00-project/vision.md`, `architecture.md`, and `constitution.md`.

Required checks:
- project mode is explicit and matches the conversation context
- core intent is specific enough to explain why this project exists now
- target user is narrower than "everyone"
- core problem names a scenario, pain, and impact
- current alternative is explicit, or the lack of validation is recorded as an open assumption
- core promise states a before/after user-visible change
- narrowest wedge is one focused validation slice
- product principles are actionable and enforceable by future feature decisions
- direction uses Now / Next / Later and does not contain date-based delivery promises
- non-goals and success signals are explicit
- open assumptions include verification ideas
- architecture constraints do not contradict the vision
- constitution principles are actionable and enforceable
- NFRs have owners or enforcement points
- placeholders and unresolved decisions are absent except documented Open Assumptions
- contradictions include source references
- first feature candidates are derived from Target User, Core Problem, Core Promise, Narrowest Wedge, Direction / Now, Success Signals, Non-goals, architecture constraints, and constitution principles
- one `recommended_first_slice` is present, or a blocker explains which product decision is missing

Required output fields:
- `reviewed_inputs`
- `input_digest`
- `evidence_refs`
- `First Feature Candidates`
- `recommended_first_slice`
- `Findings by Severity`
- `Contradiction Table`
- `blockers`
- `concerns`
- `recommended_gate_status: passed|failed|blocked`
- `recommended_next_action`

## Feature Definition Review Method
Use for `feature.md` immediately after Goal writes or updates it, before Architect runs.

Required checks:
- frontmatter scenarios exist and are non-empty
- each scenario has `id`, `story_id`, `given`, `when`, `then`, and `acceptance_refs`
- scenario IDs use `S-xxx`
- story IDs use `US-xxx`
- body declares matching `US-xxx` user stories with `Priority: P1|P2|P3`
- body declares numbered `AC-xxx` acceptance criteria
- no informal traceability IDs such as `S1`, `S2`, or unnumbered checklist-only AC are used
- scope, out-of-scope, intent review, split assessment, risk fields, and AI behavior eval fields are explicit
- Goal is a user outcome rather than only a UI element, component, or technical task
- Vision Link points to a specific `vision.md` section or success signal
- User Scenario names the workflow moment where the feature is triggered
- Proposed Options are present for standard/deep features
- Selected Approach is present before architect/design starts
- Scope and Non-goals match the selected approach

Required output fields:
- `input_refs`
- `input_digest`
- `input_digests`
- `Source Contract Checks`
- `Source Inventory`
- `Findings by Severity`
- `blockers`
- `concerns`
- `recommended_gate_status: passed|failed|blocked`
- `recommended_next_action`

## Pre-Build Review Method
Use for `feature.md`, `design.md`, and `tasks.md` before build starts.

Required checks:
- AC/scenario/task/test Coverage Matrix is complete
- Spec Convergence section is complete
- required human intent confirmation is present
- split assessment is proceed or explicitly overridden
- no scenario drift between feature and design
- no underbuild or overbuild relative to acceptance criteria
- no fake-ready task: every ready task has a complete `Execution Block`
- dependencies are ordered and have no forward dependency
- callsites and reuse obligations are explicit
- risk level matches verification depth
- implementation mode routing is consistent

Required output fields:
- `input_refs`
- `input_digest`
- `input_digests`
- `evidence_refs`
- `Coverage Matrix`
- `Dependency and Reuse Findings`
- `Readiness Findings`
- `Findings by Severity`
- `blockers`
- `concerns`
- `recommended_gate_status: passed|failed|blocked`
- `recommended_next_action`

## Gate Recommendation Rules
- `passed`: no blockers, required evidence refs are present, and the next phase can execute without inventing missing context.
- `failed`: BeWater-generated artifact omission, fake-ready task, missing coverage, or fixable internal inconsistency.
- `blocked`: user/product/architecture decision is missing or contradictory.

## Boundaries
- may not advance public lifecycle state
- may not write gates directly
