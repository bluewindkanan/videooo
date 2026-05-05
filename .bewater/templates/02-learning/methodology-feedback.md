# 方法论反馈（Methodology Feedback）

> **用途**: 从项目实践中提取 BeWater 方法论改进建议，驱动框架自进化
> **生成命令**: `/bewater-learn`
> **原则**: 不自动修改核心框架，仅提供建议供维护者审批

---

## Plan Quality Findings (plan-quality)

| # | Drift Type | Task | Evidence | Severity | Proposed Upstream Target |
|---|------------|------|----------|----------|--------------------------|
| PQ1 | ready too early | T101 | `validation-report.md#Execution Contract Audit` | high | `templates/01-features/tasks.md` |

## Must

| Target File | Change | Evidence |
|-------------|--------|----------|
| `.claude/skills/bewater-build/SKILL.md` | block build when ready task lacks `Expected RED failure marker` | `validation-report.md#Drift Summary` |

## Should

| Target File | Change | Evidence |
|-------------|--------|----------|
| `templates/02-learning/retrospective.md` | ask for ready-task drift notes | `retrospective.md` |

## Could

| Target File | Change | Evidence |
|-------------|--------|----------|
| `.claude/scripts/check-doc-consistency.sh` | warn on missing `task_readiness` in examples | `methodology-feedback.md` |

## Repeated Blockers and Evidence Gaps

| Pattern | Count | Evidence | Target File | Proposed Change | Severity |
|---------|-------|----------|-------------|-----------------|----------|
| repeated blockers | [count] | `validation-report.md#Blockers` | [file] | [change] | must|should|could |
| missing evidence categories | [count] | `validation-report.md#Drift Summary` | [file] | [change] | must|should|could |
| escaped bugs after ship | [count] | `retrospective.md#What Needs Improvement` | [file] | [change] | must|should|could |

## Backlog Export

The `must / should / could` findings above should be exported to `docs/02-learning/methodology-backlog.json`.

Each exported item must match `.bewater/contracts/methodology-backlog.schema.json` and include:

- `id`
- `severity`
- `source`
- `target_file`
- `evidence`
- `problem`
- `proposed_change`
- `status`
- `owner`
- `decision`
- `updated_at`

Allowed statuses are `open`, `accepted`, `rejected`, `planned`, and `done`.
