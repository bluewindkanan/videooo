---
name: tdd-implement
description: Stable cross-project TDD execution method
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
user-invocable: false
context: build-flow implementation
effort: medium
---

# TDD Implement

## Requires
- RED command
- GREEN target
- verify commands
- receipt path
- Eval RED/GREEN command and optional `eval_evidence` when the task includes required AI behavior eval

## Boundaries
- may produce implementation evidence
- may not mark the feature shipped
- may not advance public lifecycle state
- may not write gates directly
