---
name: product-framing
description: Reusable framing methods for goal clarification, scope challenge, and acceptance scenarios
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
user-invocable: false
context: goal-flow framing
effort: medium
---

# Product Framing

## Methods
- vision-discovery
- vision-slot-check
- intent-clarify
- scope-challenge
- acceptance-scenarios
- feature-input-classification
- feature-option-framing
- selected-approach-confirmation

## Vision Discovery
Use during `/bewater-init` to help creators discover project direction.

Rules:
- Start with project mode.
- Ask for open intent before structured fields.
- Reflect back understanding before narrowing.
- Fill fixed vision slots with adaptive questions.
- Ask one blocking question at a time.
- Prefer multiple choice when the user is unsure.
- Capture unresolved uncertainty as Open Assumptions.
- Do not create PRD language or date-based roadmap commitments.

## Feature Input Classification
Use during `/bewater-goal` before writing `feature.md`.

Classify initial input:
- Goal: user describes desired outcome.
- Solution: user describes UI, component, implementation, or workflow idea.
- Symptom: user describes a pain or failure without an outcome.

Required response:
- Goal -> propose 2-3 approaches.
- Solution -> ask which user outcome the solution serves.
- Symptom -> rewrite as candidate goal and ask for confirmation.

## Feature Option Framing
Use when the goal is clear enough to make a product decision.

Output:
- Option A: lightweight approach
- Option B: recommended balanced approach
- Option C: full approach
- Recommendation and reason
- User-selected approach

## Selected Approach Confirmation
Before `feature.md` is written or marked confirmed, the user must explicitly confirm:
- selected approach
- scope
- non-goals
- key scenarios

## Boundaries
- may structure analysis and checklists
- may not advance public lifecycle state
- may not write gates directly
