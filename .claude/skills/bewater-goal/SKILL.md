---
name: bewater-goal
description: 对话式生成功能的 feature.md（支持功能编号隔离），自动触发架构评估，Use when 需要定义功能目标或验收标准时
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
user-invocable: true
context: docs/00-project + feature scaffold + state.json
effort: medium
---

# BeWater Goal

对话式生成功能的 feature.md（整合目标与验收标准），自动触发架构评估。

## Dispatch Pattern

bewater-goal
  -> goal-flow
  -> product
  -> product-framing
  -> feature-definition-review
  -> optional architect escalation

## Notes
- `implementation_mode` remains feature classification
- `runtime.route_mode` is not written here unless the user explicitly enters quick mode later

## Completion Rule
- `feature.md` exists
- `feature.md` includes Goal, Vision Link, User Scenario, Selected Approach, Scope, Non-goals, and canonical ACs
- `feature-review.md` exists
- `feature_review_gate = passed`
- architect/design work may only start after feature review passes

## Canonical Feature Generation Contract

`/bewater-goal` must generate feature docs template-first:

1. Read and copy `templates/01-features/feature.md` into `docs/01-features/{编号}-{功能名}/feature.md`.
2. Replace placeholders in the copied template with the clarified product decisions.
3. Preserve required frontmatter keys, nested objects, and traceability fields from the template unless a field is intentionally filled with a valid value.
4. Run `python3 .claude/scripts/bewater-check.py feature --feature docs/01-features/{编号}-{功能名}/feature.md` immediately after writing.

It must not write `feature.md` from a blank file, free-form Markdown, checklist-only content, or a remembered older format. Review is a safety net, not the source of the format contract.

## Input Args
- A plain-language feature description passed by `/bewater-auto` is initial goal context.
- A numeric feature id selects or resumes that feature.
- Args do not replace interaction; goal must still clarify and confirm ambiguous product intent before writing `feature.md`.

## Product Plan Candidate Input

`/bewater-goal` may receive a product-plan candidate ID:

```text
/bewater-goal PC-001
```

When args match `PC-xxx`:

1. Read `docs/00-project/product-plan.md`.
2. Resolve the matching row from `Feature Candidate Map`.
3. Use the candidate as initial context for Feature Option Framing.
4. Treat candidate context as not approved scope: candidate context is not approved scope.
5. Still clarify user outcome, non-goals, key scenarios, risk, split assessment, and selected approach.
6. Link generated `feature.md` back to the candidate ID and vision section.
7. Do not treat product-plan candidate text as a replacement for `feature.md` acceptance criteria.

Example user-facing prompt:

```text
我从 product-plan.md 读取到 PC-001：____。
它的 MVP 目标是：____。
我会把它当成候选方向，不当成已确认 scope。
接下来我会确认用户结果、边界和关键场景，然后生成 feature.md。
```

## Human Gate: Goal Confirmation
- Draft args from `/bewater-auto` are not approved scope.
- Goal must ask clarifying questions when user intent, non-goals, or key scenarios are ambiguous.
- When `intent_review.required=true`, do not write `status: confirmed` until the user explicitly confirms:
  - user story
  - non-goals
  - key scenarios
- Record `confirmed_by`, `confirmed_at`, and `reviewed_items` when confirmation happens.

## Feature Option Framing Protocol

`/bewater-goal` is convergent requirement clarification, not open-ended vision brainstorming.

Before writing `feature.md`, classify the user's initial input:

| Input Type | Example | Required behavior |
|------------|---------|-------------------|
| Goal | "让用户更容易把 feature 需求讲清楚" | Propose 2-3 approaches with trade-offs and recommendation |
| Solution | "做一个聊天框" | Ask which user outcome this solution serves |
| Symptom | "用户老是说不清需求" | Convert the symptom into a candidate goal and ask for confirmation |

Question style:

```text
我现在的理解是：____。
这里真正影响实现的是：____。
我建议有几个方向：
A. ____
B. ____
C. ____
我推荐 __，因为 ____。
你想选哪个？
```

Required product decisions before architect/design:

- Goal is a user outcome, not a component name.
- Vision Link points to `vision.md` Core Promise, Narrowest Wedge, Product Principle, Direction / Now, or Success Signal.
- User Scenario names the workflow moment.
- Proposed Options are provided for standard/deep features.
- Selected Approach is confirmed by the user or operator.
- Scope and Non-goals are explicit.
- Acceptance Criteria remain canonical and traceable through `US-xxx → S-xxx → AC-xxx`.

Do not ask the user to invent every requirement from scratch. When the goal is clear enough, propose options and ask the user to choose.

## PM-Facing Output: Goal Brief

Default user-facing output should summarize the product decision before showing technical fields.

The Goal Brief must answer:

- Who is the user?
- What problem is being solved?
- What is in scope?
- What is explicitly out of scope?
- What are the key scenarios?
- What needs human confirmation?

Link the brief to `feature.md` and `design.md` when those artifacts exist. Internal gate names are secondary; use them only after the plain-language summary.

## When to Activate

- 需要定义新功能的目标
- 需要明确验收标准
- 需要重构现有需求
- 项目已初始化（存在 `.bewater/` 目录）

## When NOT to Activate

- 项目尚未初始化（应先运行 `/bewater-init`）
- 正在执行其他 BeWater 命令

## 职责边界（强制约束）

### ✅ 必须做

1. 解析功能编号参数（如果未提供，自动分配下一个编号）
2. 以 Product Agent 身份工作
3. 对话式引导用户定义清晰的目标
4. 挑战模糊的需求，追问"为什么"
5. 识别范围蔓延风险
6. 确保目标可验证、可量化
7. 生成 `feature.md`（整合目标与验收标准）到 `docs/01-features/{编号}-{功能名}/feature.md`（必须创建子文件夹）：先 copy `templates/01-features/feature.md`，再 replace placeholders in the copied template；must not write `feature.md` from a blank file
8. 生成 `feature.md` 时必须写入：
   - `complexity_tier: lite|standard|deep`
   - `implementation_mode: greenfield|extension|existing_partial|existing_complete`
   - `experience_surface: user_visible|internal_only|mixed`
   - `existing_implementation_note`
- 写入 `ai_behavior_eval`：
  - `applicable: true|false`
  - `required: true|false`
  - `eval_level: none|lite|standard|deep`
  - `reason`
  - `primary_risks`
  - `success_threshold`
9. 当 `implementation_mode != greenfield` 时，必须记录当前实现入口、已知缺口、是否已接近完成
10. 写入 `risk_level: critical|high|medium|low`
11. 写入 `rework_risk: critical|high|medium|low`
12. 写入 `rework_risk_factors`，至少覆盖 payment/billing、auth/permissions、data migration、public API、rollback difficulty、blast radius
13. 写入 `intent_review`：
    - `lite` 且 `risk_level=low|medium` 且 `rework_risk=low|medium` 可为 `status: not_required`
    - `standard|deep`、`risk_level=high|critical`、或 `rework_risk=high|critical` 必须为 `status: pending|confirmed|overridden`
14. 写入 `split_assessment`，并按可观测条件计算 `triggered_conditions`
15. 若 `split_assessment.triggered_conditions` 数量 >= 2，必须将 `decision` 写为 `blocked_split_required`，除非用户显式选择 `override_proceed` 并写入非空 `override_reason`
16. 生成 `feature.md` 后必须执行 Feature Definition Review：
    - 运行 `python3 .claude/scripts/bewater-check.py feature --feature docs/01-features/{编号}-{功能名}/feature.md`
    - 生成或更新 `docs/01-features/{编号}-{功能名}/feature-review.md`
    - 写入 `feature_review_gate`
17. 若 feature check 或 feature review 未通过，不得触发 `/bewater-architect`；必须修复 `feature.md` 或返回 product blocker。
18. **自动触发** `/bewater-architect {编号}` 进行架构评估，仅限 `feature_review_gate=passed` 后（传递正确路径 `docs/01-features/{编号}-{功能名}/` 与分类字段）
19. 核验 architect 已写入 `architect_gate`
20. 告诉用户"目标已定义，feature review 已通过，架构评估已触发，完成后运行 /bewater-plan 生成任务清单"

### ❌ 禁止做

1. 不能跳过对话 — 必须与用户交互
2. 不能修改项目层文档（vision.md, architecture.md）— 这是 Architect 的职责
3. 不能生成 tasks.md — 这是 Planner 的职责
4. 不能写代码 — 只定义目标
5. 禁止把多个独立用户价值强行塞进一个 feature；触发 2 个以上 split 条件时必须 blocked 或记录人工 override
6. 禁止对 required intent review 写入 `confirmed`，除非用户明确确认 user story、non-goals、key scenarios

## AI Behavior Eval Applicability

Goal must classify whether the feature includes AI behavior. Use `ai_behavior_eval.required=true` when shipped product behavior depends on LLM/model/RAG/classifier/recommender/agent output and that behavior is user-visible, decision-impacting, safety-sensitive, state-changing, or semantically judged.

Allowed `eval_level`: `none|lite|standard|deep`.

Default to:

```yaml
ai_behavior_eval:
  applicable: false
  required: false
  eval_level: none
  reason: N/A — feature has no AI/LLM/agent behavior
  primary_risks: []
  success_threshold: N/A — no AI behavior eval required
```

If AI behavior exists but risk, threshold, or user-visible impact is ambiguous, Goal must ask for clarification before confirming scope.

## 状态转换

- **前置状态**: `initialized`（项目已初始化）
- **后置状态**: `specified`（目标已定义，`feature_review_gate=passed` 后 architect 已自动触发）
- **下一步命令**: `/bewater-plan`


**版本**: 4.0.0 | **最后更新**: 2026-04-30

Semantic preflights are defined in `.claude/skills/SHARED_STATE_CONTRACT.md` under "Semantic Preflight Matrix"; run the relevant check before writing a passed gate or advancing state.
