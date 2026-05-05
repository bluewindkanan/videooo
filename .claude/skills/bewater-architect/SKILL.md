---
name: bewater-architect
description: 启动 Architect Agent 生成 design.md，并记录架构决策
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
user-invocable: false
context: feature.md + docs/00-project + architecture constraints + state.json
effort: medium
---

# BeWater Architect

为功能生成技术设计文档 `design.md`。

## Flow Ownership Note
- runs as an internal step from `goal-flow`
- may advise on structure and constraints
- may not advance public lifecycle state directly

## Trigger

- 当 feature.md 已完成且需要技术方案时使用。

## State

- 前置：`specified`
- 后置：`specified`
- 下一步：`/bewater-plan`

## Gate（强制）

1. 必须读取 `feature.md` 与项目级约束文档
2. 必须生成 `design.md`
3. 必须根据 `complexity_tier` 生成分层设计：
   - `lite`: 生成轻量 `design.md`
   - `standard`: 生成标准 `design.md`
   - `deep`: 生成标准 `design.md`，必要时补 `research.md`
4. 必须保留 `implementation_mode` 与 `existing_implementation_note`
5. 必须记录关键架构决策（decision-log/research）
6. 必须在 `design.md` 写入 Story Inventory、Scenario Coverage、Per-Story Technical Approach 与 Shared Cross-Story Concerns
7. `design.md` must include `E2E Test Strategy` with driver, scenario coverage, test asset path, data/auth setup, and artifact policy for user-visible scenarios.
8. 必须读取 `docs/00-project/constitution.md`，并在 `design.md` 写入 `Constitution Notes`
9. 必须写入 `architect_gate`，拒绝缺失 story coverage、违反项目约束或 implementation mode 不一致的设计
10. For `experience_surface=user_visible|mixed`, `design.md` must define visible entry points, discovery expectations, and minimal usage paths.
11. If `feature.md#ai_behavior_eval.applicable=true`, `design.md` must include `AI Behavior Evaluation Strategy` with scenario mapping, eval type, dataset path, scorer or rubric, eval command, threshold, result artifact, and N/A reasons for any non-applicable scenario.

## Constitution Responsibility

- Must read `docs/00-project/constitution.md`.
- Must write `Constitution Notes` in `design.md`.
- Must route clear conflicts through the existing `architect_gate` recommendation.
- Must not create a standalone constitution gate or mutate lifecycle state outside architect-flow.

## 执行步骤（最小闭环）

1. 读取 `.bewater/state.json`，检查 `current_state` 为 `specified`
2. 定位功能目录：`docs/01-features/{编号}-{功能名}/`（从 context-manifest.md 获取）
3. 调用 Architect 子代理：读取 `.claude/agents/architect.md`
4. 输入映射：`feature.md + vision.md + architecture.md (+ constitution.md)`
5. 读取 `complexity_tier` 与 `implementation_mode`
6. 产出 `design.md` 到功能目录内，并写入 `Constitution Notes`
- For AI behavior features, write `AI Behavior Evaluation Strategy`; do not choose a heavy external eval platform unless the project already uses it or the feature risk requires it.
7. 按情况补充 `research.md` 或 decision-log
8. 生成 `architect_gate`，将 gate evidence 指向 `design.md` 与必要的 `research.md`

> **路径规范**: 功能文档必须放在 `docs/01-features/{编号}-{功能名}/` 子文件夹内，禁止平铺在 `docs/01-features/` 根目录。

## 禁止事项

- 禁止写业务代码
- 禁止修改 feature.md 目标定义

## 输出合约

```json
{
  "status": "passed|failed|blocked",
  "artifacts": {
    "design_path": "...",
    "research_path": "..."
  },
  "gate": {"name": "architect_gate", "status": "passed|failed|blocked"},
  "blockers": [],
  "next_action": "/bewater-plan"
}
```
