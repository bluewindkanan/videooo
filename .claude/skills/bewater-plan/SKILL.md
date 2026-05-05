---
name: bewater-plan
description: 启动内置 Plan 子代理生成 tasks.md 并执行 Tasks Gate
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
user-invocable: true
context: feature.md + design.md + tasks gate + state.json
effort: medium
---

# BeWater Plan

为功能生成任务清单（tasks.md），通过 Tasks Gate。

## Dispatch Pattern

bewater-plan
  -> plan-flow
  -> planner
  -> planning-readiness
  -> review-pack
  -> prebuild_review_gate

## Completion Rule
- `tasks_gate = passed`
- `prebuild_review_gate = passed`
- `design.md` must exist for `greenfield`, `extension`, `existing_partial`, and `existing_complete`
- If `design.md` marks any scenario as E2E required, `tasks.md` must include a `Testing Asset Map`.
- A ready E2E test asset task must include spec path, RED command, verify command, runtime setup, artifact policy, and `receipts.json#Txxx`.
- If `feature.md#ai_behavior_eval.required=true`, `tasks.md` must include an `Eval Asset Map`.
- A ready AI eval asset task must include dataset path, scorer or rubric, Eval RED command, verify command, result artifact, and `receipts.json#Txxx.eval_evidence`.

## PM-Facing Output: Build Plan

Default user-facing output should explain the build in product terms before showing task mechanics.

The Build Plan must answer:

- What will the agent build?
- What files or modules are in scope?
- What tests will prove it works?
- What are the main risks?
- What would cause the build to stop?

Link the summary to `tasks.md` and `prebuild-review.md`. Internal gate names are secondary; use them only after the plain-language summary.

Black-box verification levels:
- `static_verify`: build, typecheck, lint, grep, source inspection, file counts; never enough for a user-visible scenario by itself.
- `blackbox_smoke`: minimal boundary check through rendered HTML, API, CLI, or service request.
- `formal_e2e`: durable committed E2E test asset, Playwright by default for Web/UI.
- `exploratory_browser`: supplemental `agent-browser` evidence only; agent-browser is supplemental and must not replace planned `formal_e2e` or `blackbox_smoke`.

## Trigger
- 当 feature.md + design.md 已就绪，需要任务拆解时使用。

## State
- 前置：`specified`
- 后置：`planned`
- 下一步：`/bewater-build`（`existing_complete` 允许 `/bewater-validate`）

## 执行步骤
1. 读取 `.bewater/state.json`，定位功能目录 `docs/01-features/{编号}-{功能名}/`
2. 调用 Plan 子代理，传入 `feature.md + design.md`
3. 读取 `complexity_tier` 与 `implementation_mode`
4. 按模式生成 `tasks.md`：
   - `greenfield`: 正常实现任务
   - `extension`: reuse analysis + callsite inventory + regression coverage tasks
   - `existing_partial`: gap analysis + 定向修复任务 + 证据补齐任务
   - `existing_complete`: audit / review / validate 准备任务；仅在发现实现缺口时增加代码任务
5. 生成 `tasks.md`，每个任务至少包含：
   - story ID（如 `US-001`）
   - scenario ID 或 AC reference（如 `S-001` / `AC-001`）
   - AC 映射
   - 测试映射（unit/integration/e2e）
   - 依赖关系
   - 风险标注
6. 以下场景必须显式补子清单：
   - 登录跳转：写清 `callbackUrl`
   - 未登录行为：写清 redirect/拦截策略
   - 删除/清空/取消收藏：写清 confirmation
   - Props/共享 API 变更：列出所有调用点
7. 可并行任务增加 `parallel_group`
8. 共享函数/模块增加 `reuse_checklist`
9. 对当前 next dispatchable ready task，或 next dispatchable parallel batch，必须展开 `Execution Block`
10. `Execution Block` 至少包含：
   - `Story / scenario refs`
   - `Design refs`
   - `Exact files in scope`
   - `Callsites / reuse checklist`
   - `RED command`
   - `Expected RED failure marker`
   - `GREEN target`
   - `Verify commands`
   - `Receipt path`
   - `Done definition`
   - `Escalation notes`
11. 每个任务必须显式写 `task_readiness: backlog | ready | in_progress | done`
12. 对未 ready task，可保留 Delivery-Map 骨架；但进入 ready 后不得缺少 `Execution Block`
13. 生成 `tasks.md` 后，必须执行 pre-build readiness review（feature.md + design.md + tasks.md 联合审查）
14. `tasks_gate=passed` 仅表示下一组 dispatchable ready tasks 已可直接进入 build（planner 无需再补齐执行细节）
15. `prebuild_review_gate` 必须联合审查 `feature.md`、`design.md`、`tasks.md`，阻断故事遗漏、scenario drift、underbuild/overbuild 与 fake-ready tasks
16. 必须读取 `docs/00-project/constitution.md`，并在 `tasks.md` 写入 `Constitution Compliance Notes`
17. 生成或更新 `prebuild-review.md`
18. 在 `prebuild-review.md` 写入 `Spec Convergence`
19. 在 `prebuild-review.md` 写入全局 `Coverage Matrix`
20. 若 `intent_review.required=true` 且 `status` 不是 `confirmed|overridden`，`prebuild_review_gate=blocked`
21. 若 split assessment 触发 2 个以上条件且未 `override_proceed`，`prebuild_review_gate=blocked`
22. 若任一 scenario 缺 design/task/test 覆盖，`prebuild_review_gate=failed`
23. 若 ready task 缺完整 test mapping 或 Execution Block，`tasks_gate=failed`
24. 若 `experience_surface=user_visible|mixed`，必须检查 discoverability affordance 与 minimal usage path 已被 design/task 覆盖；缺失时 `prebuild_review_gate=failed|blocked`

## Constitution Responsibility

- Must read `docs/00-project/constitution.md`.
- Must write `Constitution Compliance Notes` in `tasks.md`.
- Must route clear conflicts through the existing `tasks_gate` or `prebuild_review_gate` recommendation.
- Must not create a standalone constitution gate or mutate lifecycle state outside plan-flow.

## Gate（强制）
1. 必须存在 `feature.md` 与 `design.md`
2. tasks.md 至少包含 1 个任务
3. 每个任务必须具备 story ID、scenario/AC 映射、测试、依赖、风险
4. 每个任务必须声明 `task_readiness`
5. ready task 必须包含完整 `Execution Block`
6. `Pre-Build Readiness Review` 必须完成；planner-owned omission 应判为 `failed`；设计/边界未决应判为 `blocked`
7. `prebuild-review.md` 必须存在并包含 `Spec Convergence`
8. `Coverage Matrix` 必须覆盖 feature 中的每个 scenario
9. required `intent_review` 未确认时不得进入 build
10. split assessment 未通过或未 override 时不得进入 build
11. `Constitution Compliance Notes` 必须存在；明显原则冲突需通过现有 `failed|blocked` 路径处理
12. Required AI behavior eval without `AI Behavior Evaluation Strategy` or `Eval Asset Map` is `spec_package_drift` and must not enter build.

## 禁止事项
- 禁止修改 feature.md
- 禁止写业务代码

## 状态变更指令（强制）
```json
{
  "current_state": "planned",
  "planned_at": "[ISO日期]",
  "current_feature": "[编号]-[名称]",
  "artifacts": {"tasks_path": "docs/01-features/[编号]-[名称]/tasks.md"},
  "gates": {"tasks_gate": {"status": "passed", "blockers": [], "updated_at": "[ISO时间]"}},
  "next_command": "/bewater-build | /bewater-validate"
}
```

## 输出合约
```json
{
  "status": "passed|failed|blocked",
  "artifacts": {"tasks_path": "..."},
  "gate": {"name": "tasks_gate", "status": "passed|failed|blocked"},
  "blockers": [],
  "next_action": "/bewater-build | /bewater-validate",
  "task_count": 0,
  "parallel_groups": []
}
```

Semantic preflights are defined in `.claude/skills/SHARED_STATE_CONTRACT.md` under "Semantic Preflight Matrix"; run the relevant check before writing a passed gate or advancing state.
