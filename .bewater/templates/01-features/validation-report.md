# Validation Report

> **用途**: `/bewater-validate` 生成的可审计验证证据，供 `/bewater-ship` 消费

feature: [feature-id]
validation_outcome.classification: ready_for_precheck|evidence_incomplete_or_stale|implementation_gap|spec_package_drift|goal_scope_contradiction
validation_outcome.release_decision: go|no-go
release_readiness: ready_for_precheck|not_ready

---

## Summary

- validated_at: [YYYY-MM-DD HH:mm:ss]
- validator: [Agent/姓名]
- overall_status: passed|failed|blocked
- review_note_path: [docs/01-features/{编号}-{名称}/review-note.md]

## AC Coverage

| AC | 验证方式 | 结果 | 备注 |
|----|---------|------|------|
| AC-1 | [测试/QA/手动] | pass/fail | [说明] |

## Commands

| 命令 | 结果 | 摘要 |
|------|------|------|
| `npm test` | pass/fail | [说明] |
| `npm run build` | pass/fail | [说明] |

## Coverage Summary

- coverage_source: [vitest/jest/pytest-cov/lcov/N/A]
- overall_line_coverage: [例如 88% / N/A]
- overall_branch_coverage: [例如 72% / N/A]
- notes: [说明覆盖率产物来源或为什么不适用]

## Low Coverage Files

> 当存在覆盖率产物且单文件 Branch 覆盖率低于 60% 时，至少列出 INFO 级提醒；若无覆盖率产物，写明 `N/A`。

| 文件 | 指标 | 当前值 | 阈值 | 等级 | 备注 |
|------|------|--------|------|------|------|
| [path/to/file] | branch | [42%] | 60% | info | [说明] |

## E2E 测试结果

> QA 运行 Builder 在 Build 阶段提交的 E2E 测试资产和 black-box 测试资产；若缺少正式测试文件或 black-box smoke 命令，应判定为 `implementation_gap` 并回到 `/bewater-build`。
> `static_verify` 只能作为补充证据，不能替代用户可见边界验证。
> `agent-browser is supplemental`: `exploratory_browser` 截图和操作记录可以补充验证，但不能替代计划中的 `formal_e2e` 或 `blackbox_smoke`。

| Scenario | Level | Spec file or smoke command | Command | Receipt | Result | Artifacts | Notes |
|----------|-------|----------------------------|---------|---------|--------|-----------|-------|
| S-001 | blackbox_smoke / formal_e2e / exploratory_browser | `e2e/flows/example.spec.ts` or `curl -fsS http://127.0.0.1:5173/` | `npx playwright test e2e/flows/example.spec.ts --grep "@S-001"` | `receipts.json#T201` | pass/fail | `test-results/.../trace.zip` or command log | QA command output summary |

## AI Behavior Evaluation Results

> Required when `feature.md#ai_behavior_eval.required=true`.
> Validate only runs and audits planned AI eval assets; it must not create required eval datasets, rubrics, or runners during Validate.
> Missing required eval assets are `implementation_gap`. Non-runnable or stale eval evidence is `evidence_incomplete_or_stale`. Scores below threshold require `release_decision: no-go`.

| Scenario | Eval Level | eval command | dataset | scorer or rubric | score | threshold | Result | Receipt | Artifacts | Notes |
|----------|------------|--------------|---------|------------------|-------|-----------|--------|---------|-----------|-------|
| S-001 | none / lite / standard / deep | `npm run eval:{feature-id}` | `evals/{feature-id}/golden.jsonl` | `evals/{feature-id}/rubric.md` | `0.84` | `overall >= 0.80 and safety = pass` | pass/fail/N/A | `receipts.json#T201.eval_evidence` | `eval-results/{feature-id}.json` | N/A — no AI behavior eval required by default |

## Discoverability & Usage Path

> `experience_surface=user_visible|mixed` 时必填。技术能力存在但用户无法发现或走通最小路径时，不得判定为 release-ready。

| Scenario | Entry point | Discoverability evidence | Completion-path evidence | Result | Failure class | Notes |
|----------|-------------|--------------------------|--------------------------|--------|---------------|-------|
| S-001 | Header nav / settings / CLI help | rendered UI / help output / docs link | smoke or E2E evidence | pass/fail | implementation_gap/spec_package_drift/goal_scope_contradiction | [summary] |

## Constitution Alignment

- checked_against: `docs/00-project/constitution.md`
- result: pass|warn|fail|not_applicable
- evidence:
  - `npm test` passed and review-note.md found no principle conflict.
- notes:
  - No direct constitution conflict was observed during validation.
  - If result is fail, add the issue to Blockers and set `release_decision: no-go`.

## Spec Consistency

| 检查项 | 结果 | 备注 |
|--------|------|------|
| feature 与实现一致 | pass/fail | [说明] |
| design 与实现一致 | pass/fail | [说明] |

## Execution Contract Audit

| 任务 | Receipt | Scope Match | RED/GREEN/Verify | Done Definition | 结果 | 备注 |
|------|---------|-------------|------------------|-----------------|------|------|
| T101 | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | [说明] |

## Drift Summary

| 类型 | 任务 | 结果 | 说明 |
|------|------|------|------|
| minor drift | T101 | warn | [说明] |
| material drift | T201 | fail | [说明] |

## Documentation Freshness Evidence

> Feature docs are historical delivery claims. Use this section to record whether the current code still supports treating them as fresh context.

- last_verified_commit: [git sha or null]
- last_verified_at: [YYYY-MM-DD HH:mm:ss or null]
- docs_freshness: fresh|docs_may_be_stale|unknown
- stale_reason: [N/A — fresh, or implementation path changed after last_verified_commit]

| implementation_paths | Last change evidence | Freshness |
|----------------------|----------------------|-----------|
| `path/to/file` | [commit/date/command output] | fresh/docs_may_be_stale/unknown |

## Planning Findings

- [ ] 哪些任务被过早标成 `ready`
- [ ] 哪些 `Execution Block` 字段缺失或失真
- [ ] 哪些 scope / verify / done definition 不能审计

## Recommended Methodology Feedback

- must: [需要回写的上游契约]
- should: [应优化的模板或 skill]
- could: [可选增强项]

## Security Checks

- [ ] 输入校验
- [ ] 权限控制
- [ ] 敏感信息泄露检查

## Performance Checks

| 指标 | 基线 | 当前 | 结果 |
|------|------|------|------|
| p95 | [值] | [值] | pass/fail |

## Lighthouse Report

> Web / frontend 项目必须填写；非 Web 项目填写 `N/A` 与原因。

- applicable: [yes/no]
- reason_if_na: [非 Web 项目可填]

| 指标 | 目标 | 实际 | 结果 |
|------|------|------|------|
| Performance Score | ≥ 90 | [值/N/A] | pass/fail |
| LCP | ≤ 2.5s | [值/N/A] | pass/fail |
| INP | ≤ 200ms | [值/N/A] | pass/fail |
| CLS | ≤ 0.1 | [值/N/A] | pass/fail |

## Final Review Evidence

- review_gate_decision: passed|failed|blocked
- review_note_path: [docs/01-features/{编号}-{名称}/review-note.md]

## Blockers

- [ ] [阻断项]

## Gate Summary

- release_readiness: ready_for_precheck|not_ready
- evidence_checked: false
- next_action: `/bewater-ship | /bewater-build`
