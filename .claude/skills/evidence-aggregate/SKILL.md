---
name: evidence-aggregate
description: Evidence normalization and aggregation shared by validate, ship precheck, and CI wrappers
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
user-invocable: false
context: validate-flow and ship-flow evidence packaging
effort: medium
---

# Evidence Aggregate

## Responsibilities
- normalize evidence refs
- summarize artifacts
- prepare machine-readable evidence lists
- normalize eval result artifacts from planned AI behavior eval suites

## Boundaries
- may not write public state
- may not decide release legality
- may not advance public lifecycle state
- may not write gates directly
