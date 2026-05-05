---
name: bewater-validate
description: 执行 QA（含安全+性能+Spec一致性）验证并生成 validation-report.md
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
user-invocable: true
context: feature.md + tasks.md + validation evidence + state.json
effort: high
---

# BeWater Validate

validate 负责生成可审计的 `validation-report.md`，供 ship 消费。

命令入口：`/bewater-validate`
执行归属：`validate-flow`

## Public Command

`/bewater-validate` is a public lifecycle command in the standard delivery path:

```text
goal -> plan -> build -> validate -> ship
```

Validate produces `validation-report.md` and `runtime.validation_outcome`. It must not write `ship_precheck_gate`, move state to `shipped`, or perform irreversible release actions.

## Output Contract
- must write `validation-report.md`
- must write structured `validation_outcome`
- must not write `ship_precheck_gate`
- does not perform irreversible release

## Trigger
- 发布前质量验证时使用。

## State
- 前置：`building`
- 例外：`planned` 且 `implementation_mode=existing_complete`，或 `existing_partial` 且无剩余实现缺口
- 后置：`building`
- 下一步：`/bewater-ship` 或 `/bewater-build`

## Gate（强制）
1. 必须执行 QA
2. 必须执行 Spec 一致性检查
3. 必须输出 `validation-report.md`
4. 有 P0/P1 blocker 时必须 `release_decision: no-go`
5. `high|critical` 功能必须有完整 E2E，不能只 smoke
6. 如存在覆盖率产物，必须记录总体覆盖率；单文件 Branch 覆盖率低于 60% 时必须在报告中标注
7. Web / frontend 项目必须记录 Lighthouse 证据；不适用时必须写明 `N/A` 原因
8. Validate must run existing E2E assets produced by Build and map results to scenario, spec file, command, receipt, and artifacts.
9. Missing planned E2E assets are `implementation_gap`, not an invitation for QA to write formal tests during Validate.
10. 必须读取 `docs/00-project/constitution.md`，并在 `validation-report.md` 写入 `Constitution Alignment`
11. For `experience_surface=user_visible|mixed`, Validate must record discoverability evidence and minimal usage-path evidence; technical existence alone is not sufficient for `release_decision: go`.
12. If `feature.md#ai_behavior_eval.required=true`, Validate must write `AI Behavior Evaluation Results`, run the planned eval command, audit dataset/scorer/threshold/receipt/artifacts, and set `release_decision: no-go` when required eval evidence is missing or below threshold.

## Constitution Responsibility

- Must read `docs/00-project/constitution.md`.
- Must write `Constitution Alignment` in `validation-report.md`.
- Must route clear conflicts through existing `Blockers` and `release_decision: no-go`.
- Must not create a standalone constitution gate or mutate lifecycle state outside validate-flow.

Black-box verification levels:
- `static_verify`: build, typecheck, lint, grep, source inspection, file counts; never enough for a user-visible scenario by itself.
- `blackbox_smoke`: minimal boundary check through rendered HTML, API, CLI, or service request.
- `formal_e2e`: durable committed E2E test asset, Playwright by default for Web/UI.
- `exploratory_browser`: supplemental `agent-browser` evidence only; agent-browser is supplemental and must not replace planned `formal_e2e` or `blackbox_smoke`.

## 执行步骤
1. 读取 `.bewater/state.json`，确认 `current_state=building`；若处于 `planned` 例外路径，必须先把状态写为 `building`
2. 读取 `feature.md` 的 `risk_level`（默认 `high`）
3. 读取 `implementation_mode`，确认是否属于 existing implementation 例外路径
4. 按风险选择验证深度：
   - Low：smoke + AC + 轻量 spec
   - Medium：标准 QA + spec + smoke/guest E2E
   - High/Critical：完整 QA + spec + 完整 E2E
5. 调用 QA 子代理，输入 `feature.md + tasks.md + design.md`
6. 根据 `architecture.md` 中的技术栈选择对应的高频问题检查项（通用项：未登录跳转、destructive confirmation、共享 API 回归、`as any`；Web 框架特有项：按 architecture.md 中声明的框架选择）
7. 如果存在覆盖率报告（如 lcov / cobertura / vitest / jest coverage），提取：
   - overall line / branch coverage
   - 单文件 Branch 覆盖率 < 60% 的文件清单（按 INFO 记录，不自动阻断）
8. 如果是 Web / frontend 项目，执行 Lighthouse 或等效性能检查，并记录：
   - Performance score
   - LCP
   - INP
   - CLS
   非 Web 项目则写 `N/A` 与原因
9. 在产出 `validation-report.md` 前，执行 `Execution Contract Audit`：
   - receipt 是否存在且字段完整
   - `files_changed` 是否落在 `Exact files in scope` 内，超范围是否有解释
   - `RED/GREEN/Verify` 是否存在真实执行证据
   - `Callsites / reuse checklist` 是否已完成
   - `Done definition` 是否可审计
10. 将 drift 分类为：
   - `minor drift`：可带 warning 继续 ship
   - `material drift`：必须回到 build 补证据或修边界
11. 在报告中写出：
   - `Constitution Alignment`
   - `Discoverability & Usage Path`
   - `Execution Contract Audit`
   - `Drift Summary`
   - `Planning Findings`
   - `Recommended Methodology Feedback`
12. Validate only runs and audits planned AI eval assets. It must not create required eval datasets, rubrics, or runners during Validate. Missing required eval assets are `implementation_gap`; stale or non-runnable eval evidence is `evidence_incomplete_or_stale`; missing eval strategy or asset map is `spec_package_drift`.
13. 如果 `Constitution Alignment` 为 `fail`，必须写入 `Blockers` 并设置 `release_decision: no-go`
14. 生成 `validation-report.md`
15. 更新 `.bewater/state.json`：
   - `runtime.validation_outcome=...`
   - `artifacts.validation_report_path=...`
   - 不写入 `ship_precheck_gate`；release gate 由 `/bewater-ship` 根据 `validation_outcome` 合成

## `validation-report.md` 最小结构
```markdown
# Validation Report
feature: [编号]-[名称]
risk_level: low|medium|high|critical
release_decision: go|no-go

## AC Coverage
## Commands
## Coverage Summary
## Low Coverage Files
## E2E 测试结果
## AI Behavior Evaluation Results
## Constitution Alignment
## Spec Consistency
## Execution Contract Audit
## Drift Summary
## Planning Findings
## Recommended Methodology Feedback
## Lighthouse Report
## Blockers
```

## 禁止事项
- 禁止跳过 Spec consistency
- 禁止省略执行命令与结果
- 禁止 high/critical 只做 smoke E2E
- 禁止忽略已存在的覆盖率产物
- 禁止 Web / frontend 项目省略 Lighthouse 证据或 `N/A` 说明

## PM-Facing Output: Validation Dossier

Default user-facing output should describe release readiness through evidence, not gate jargon.

The Validation Dossier must answer:

- Did technical checks pass?
- Did user-visible discovery pass?
- Did the minimal usage path pass?
- What black-box or E2E evidence exists?
- What blockers remain?

Link the summary to `validation-report.md`, `review-note.md`, and relevant test/coverage artifacts. Internal gate names are secondary; use them only after the plain-language summary.

## 输出合约
```json
{
  "status": "passed|failed|blocked",
  "artifacts": {"validation_report_path": "..."},
  "validation_outcome": {
    "classification": "ready_for_precheck|evidence_incomplete_or_stale|implementation_gap|spec_package_drift|goal_scope_contradiction",
    "release_decision": "go|no-go",
    "decider": "qa|reviewer|planner|product",
    "consulted_roles": [],
    "evaluated_at": "[ISO时间]",
    "recommended_next_action": "/bewater-ship|/bewater-build|/bewater-plan|/bewater-goal",
    "evidence_refs": [],
    "blockers": []
  },
  "blockers": [],
  "next_action": "/bewater-ship | /bewater-build",
  "risk_level": "low|medium|high|critical",
  "release_decision": "go|no-go",
  "coverage_summary": {"line": "0-100%", "branch": "0-100%"},
  "low_coverage_files": [{"path": "...", "branch": "42%"}],
  "lighthouse_required": true
}
```
