---
name: bewater-build
description: 启动 Builder Agent 执行 TDD 实现，并自动触发 review
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
user-invocable: true
context: tasks.md + design.md + state.json + review checkpoints
effort: high
---

# BeWater Build

以 TDD 实现功能。主代理只负责调度、核验、状态回写；不直接写实现代码。

## Gate Ownership
- `prebuild_review_gate` must already be `passed`
- `review_gate` may only be written by `build-flow`
- when code is already complete but review evidence is stale or missing, `build-flow` may run a review-only path

## Trigger

- `tasks.md` 已生成并进入实现阶段时使用。
- existing implementation 模式下，用于补实现缺口、补测试、补回归，而不是重写整个功能。

## State

- 前置：`planned`（允许 `building` 续跑）
- 后置：`building`
- 下一步：`/bewater-validate`
- 后续链路：`/bewater-validate` 生成/刷新验证证据，随后 `/bewater-ship` 核验证据与 release gate

## Gate（强制）

1. 所有实现任务必须通过 Builder 子代理执行
2. Builder 必须遵循 TDD
3. checkpoint 必须触发 incremental review
4. 全部任务完成必须触发 final review
5. 主代理必须核验关键文件已落盘；`shared_api_changed=true` 时必须执行全量回归；关键测试/编译已通过
6. existing implementation 模式下，build 只负责补缺口，不能把已有实现当作重写任务重新铺开
7. 每个已实现任务必须生成 JSON TDD 回执，并通过 `.claude/scripts/check-tdd-receipts.py` 校验
8. formal E2E test code is a Build artifact when planned.
9. Builder must run the E2E RED command before implementation and record RED/GREEN/VERIFY evidence in `receipts.json`.
10. final review 前必须执行 build completion guard：`python3 .claude/scripts/check-task-execution-readiness.py --tasks docs/01-features/{id-name}/tasks.md --require-build-complete`
11. If a ready task includes a required AI behavior eval asset, Builder must run Eval RED/GREEN before treating the task as done.
12. Required AI behavior eval assets are Build artifacts: dataset, scorer or rubric, eval runner, result artifact, and optional `eval_evidence` in `receipts.json#Txxx`.

Black-box verification levels:
- `static_verify`: build, typecheck, lint, grep, source inspection, file counts; never enough for a user-visible scenario by itself.
- `blackbox_smoke`: minimal boundary check through rendered HTML, API, CLI, or service request.
- `formal_e2e`: durable committed E2E test asset, Playwright by default for Web/UI.
- `exploratory_browser`: supplemental `agent-browser` evidence only; agent-browser is supplemental and must not replace planned `formal_e2e` or `blackbox_smoke`.

## 执行步骤

1. 检查 `.bewater/state.json` 为 `planned|building`
2. 读取 `feature.md + design.md + tasks.md`
3. 读取 `implementation_mode`
4. 按模式执行：
   - `greenfield`：正常实现
   - `existing_partial`：补实现缺口、补测试、补回归
   - `existing_complete`：通常跳过；只有 review / validate 发现真实实现缺口时才回到 build
5. 解析 `task_readiness`、依赖与 `parallel_group`，得到 next dispatchable ready set（或 next dispatchable parallel batch）
6. 在调度 Builder 前，先核验该 ready set 的每个任务都具备完整 `Execution Block`
7. 任一任务缺字段时，build does not start；不进入实现；结果应为 planner-side fix 或 blocker，而不是 Builder 自行脑补
8. 按依赖与并行组调度 Builder
9. Builder prompt 必须注入：复用清单、调用点清单、风险等级
10. Builder 输出必须包含：
   - `files_verified`
   - `callsites_checked`
   - `shared_api_changed`
   - `type_escape_used`
   - `write_edit_permission_denied`
   - `completion_state`（`done | done_with_concerns | needs_context | blocked`）
   - `concerns`
11. 主代理核验：
   - 关键文件确实存在；未落盘时最多重试 Builder 1 次
   - `write_edit_permission_denied=true` 时不重试，由主代理 fallback
   - `shared_api_changed=true` 时必须执行全量回归
   - `type_escape_used=true` 时直接阻断
12. 按 `completion_state` 调度：
   - `done`：进入 spec review
   - `done_with_concerns`：先处理 concern，再进入 spec review
   - `needs_context`：主代理补充上下文后重派
   - `blocked`：停止并返回阻断原因
13. Build review order 固定为：
   1. implementer
   2. spec review
   3. code quality review
   4. 任一 review 失败都必须回到 implementer 修复，再重新 review
14. checkpoint 触发 `/bewater-review --type incremental`
15. 每个 Builder batch 后必须重新读取 `tasks.md` 并回到步骤 5；若仍有 unfinished planned task，不得进入 final review
16. 若依赖已满足但任务仍是 `backlog`，build must stop and route to `/bewater-plan` to promote/expand the task；不得把它当作已完成
17. 全部任务完成后，先运行 `python3 .claude/scripts/check-task-execution-readiness.py --tasks docs/01-features/{id-name}/tasks.md --require-build-complete`
18. completion guard 通过后才触发 `/bewater-review --type final`
19. 仅在核验成功后写入/保持 `building`，并把下一步设为 `/bewater-validate`

> 对 existing implementation 模式，build 表示“补缺口”，不是“重写整个功能”。

## TDD Evidence 合约（强制）

每个实现任务都必须写入 JSON TDD 回执，字段至少包含：
- `task_id`
- `red_command`
- `red_exit_code`
- `red_failure_marker`
- `green_command`
- `green_exit_code`
- `verify_commands`
- `files_under_test`
- `files_changed`
- `recorded_at`

标准位置：`docs/01-features/{id-name}/receipts.json#T{xxx}`（每个 feature 一个 receipts.json）

完成实现阶段前必须执行：
`python3 .claude/scripts/check-tdd-receipts.py --tasks docs/01-features/{id-name}/tasks.md --receipts docs/01-features/{id-name}/receipts.json`

Before a completed implementation task can be treated as done, run `.claude/scripts/check-tdd-receipts.py` against the feature `tasks.md` and single `receipts.json`. Receipts must match `.bewater/contracts/tdd-receipt.schema.json`; old prose-only fields do not satisfy the contract.

## Builder 阻断条件

- 新增 `as any` / 类型逃逸
- Props / 共享 API 变更未同步全部调用点
- 已有工具函数被重复实现
- 回执字段缺失
- Required AI behavior eval asset missing, eval command not run, or `eval_evidence` missing from the task receipt
- 文件未落盘且 1 次重试后仍失败
- Write/Edit 权限失败

## 状态变更指令（强制）

```json
{
  "current_state": "building",
  "building_at": "[ISO日期]",
  "current_feature": "[编号]-[名称]",
  "internal_stage": "reviewing|implementing",
  "artifacts": {
    "review_note_path": "docs/01-features/[编号]-[名称]/review-note.md"
  },
  "gates": {
    "review_gate": {"status": "passed|failed|blocked", "blockers": [], "updated_at": "[ISO时间]"}
  },
  "next_command": "/bewater-build | /bewater-validate"
}
```

## 输出合约

```json
{
  "status": "passed|failed|blocked",
  "artifacts": {"tasks_path": "...", "review_summary": "..."},
  "gate": {"name": "review_gate", "status": "passed|failed|blocked"},
  "blockers": [],
  "next_action": "/bewater-build | /bewater-validate",
  "review_type": "incremental|final",
  "builder_receipts": [{
    "status": "passed|failed|blocked",
    "completion_state": "done|done_with_concerns|needs_context|blocked",
    "concerns": [],
    "tasks_completed": [],
    "files_verified": true,
    "callsites_checked": true,
    "shared_api_changed": false,
    "type_escape_used": false,
    "write_edit_permission_denied": false
  }]
}
```

Semantic preflights are defined in `.claude/skills/SHARED_STATE_CONTRACT.md` under "Semantic Preflight Matrix"; run the relevant check before writing a passed gate or advancing state.
