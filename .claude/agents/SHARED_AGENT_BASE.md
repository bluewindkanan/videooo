---
name: shared-agent-base
agentType: shared-base
description: BeWater 所有 Agent 共用的协议、输出契约和上下文预算纪律
whenToUse: 供 product/architect/builder/reviewer/qa/inspector 通过 base 引用，不直接单独调度
version: 4.0.0
role: Shared Protocol
phase: Shared
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
effort: small
color: gray
---

# Shared Agent Protocol (v4.0.0)

> 所有 Agent 的共享规范。各 Agent .md 仅定义独特逻辑，本文件定义通用协议。

## 输出合约

完成后**只输出 JSON 摘要**，字段遵循调用 skill 的本地合约：

```json
{
  "status": "passed|failed|blocked",
  "artifacts": {},
  "recommended_gate_status": "passed|failed|blocked|go|no-go",
  "blockers": [],
  "next_action": "..."
}
```

## State Mutation Boundary

Agents recommend; Skills mutate state.

Agents must not write `.bewater/state.json`, must not change lifecycle state, and must not emit canonical `gate` objects as if they were already persisted. Use `recommended_gate_status` when a gate decision is relevant.

Recommended output shape:

```json
{
  "status": "passed|failed|blocked",
  "recommendation": "go|no-go|passed|failed|blocked",
  "recommended_gate_status": "go|no-go|passed|failed|blocked",
  "evidence_refs": [],
  "blockers": [],
  "notes": []
}
```

## 上下文预算纪律

**文档读取优先级**（上下文紧张时按顺序跳过）：
1. Current feature execution artifacts: `feature.md` + `tasks.md` + current state（执行期必读）
2. Project constraints: `docs/00-project/project-context.md` + `docs/00-project/constitution.md` + phase-relevant `architecture.md`（design/planning/validation/review 决策时必读）
3. Feature design and evidence artifacts: `design.md` + `prebuild-review.md` + `review-note.md` + `validation-report.md`（按阶段读取）
4. Historical feature docs（只有 freshness evidence 支持时才作为当前系统事实）

`constitution.md` is not optional for design, planning, validation, or review decisions. If it cannot be loaded, record a blocker or concern in the role's normal output instead of silently skipping it.

**任务分割**：剩余任务 > 3 时，输出 JSON 摘要并请求重新调用。

## Memory Protocol

- **启动时**：读取 `.claude/agent-memory/{role}/MEMORY.md`。如存在，应用其中记录的经验。
- **完成时**：如发现新模式/陷阱，追加一行到同文件。文件总行数 ≤ 50。

## 禁止事项（所有 Agent 通用）

- 禁止执行职责边界外的工作
- 禁止修改非职责范围的文件
- 禁止跳过 Gate 检查
- must not write `.bewater/state.json`
- must not emit canonical `gate` objects

## Global Boundaries
- agents own judgments, not lifecycle progression
- only flows write public state
- capability packs are advisory methods, not authorities
