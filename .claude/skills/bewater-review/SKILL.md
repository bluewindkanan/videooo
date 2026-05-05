---
name: bewater-review
description: 启动 Reviewer Agent 执行代码审查（incremental|final）
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
user-invocable: false
context: feature.md + tasks.md + review gate + state.json
effort: medium
---

# BeWater Review

执行代码审查。由 build/quick 自动触发。

## Ownership
- internal only
- called by `build-flow`
- may inform `review_gate`
- may not advance lifecycle state on its own

## Trigger

- Build checkpoint（incremental）或 Build/Quick 在 validate 前的 final review 时使用。

## State

- 前置：`building`
- 后置：`building`（incremental）或保持验证前门禁结果
- 下一步：继续 build 或进入 `/bewater-validate`

## Gate（强制）

1. 审查范围按风险等级执行（高风险全量）
2. 必须在 tasks.md 记录审查结论
3. 审查决策输出 `go|no-go`
4. 仅在 `Pre-Build Readiness Review` 已通过后进入 build review
5. final review 必须先运行 `python3 .claude/scripts/check-task-execution-readiness.py --tasks docs/01-features/{id-name}/tasks.md --require-build-complete`；发现 unfinished planned task 时直接 `blocked`

## 执行步骤（最小闭环）

1. 解析 `--type`
2. 读取 `.bewater/state.json`，检查 `current_state` 为 `building`
3. 若 `--type final`，先运行 build completion guard；未通过时输出 unfinished planned task blocker，并返回 `/bewater-build | /bewater-plan`
4. 调用 Reviewer 子代理：读取 `.claude/agents/reviewer.md`
5. 输入映射：`tasks.md + feature.md + architecture.md + review_type`
6. build review 顺序固定：先 spec review，再 code quality review
7. 任一审查失败都返回 build 修复并再次审查
8. 仅输出审查结论，不改代码

## 禁止事项

- 禁止修改代码（只审查不改代码）

## 输出合约

```json
{
  "status": "passed|failed|blocked",
  "artifacts": {"review_note_path": "..."},
  "gate": {"name": "review_gate", "status": "passed|failed|blocked"},
  "blockers": [],
  "next_action": "/bewater-build | /bewater-validate",
  "review_type": "incremental|final",
  "gate_decision": "go|no-go"
}
```
