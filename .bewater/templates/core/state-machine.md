# BeWater 状态机完整定义

版本: 4.0.0 | 日期: 2026-04-21

## 公开状态链

`uninitialized → initialized → specified → planned → building → shipped`

## 状态定义

1. **uninitialized** - 项目未初始化，缺少项目层文档
2. **initialized** - 项目级文档已建立
3. **specified** - 功能目标与设计已明确
4. **planned** - `tasks.md` 已通过 `tasks_gate`，且至少存在一组 execution-ready tasks
5. **building** - 正在实现、review 或补验证证据
6. **shipped** - 发布完成，且证据已核验

---

## building 内部子阶段

```text
building.implementing
building.reviewing
building.validating
building.ready_to_ship
```

---

## Gate 定义

| Gate 名称 | 触发时机 | 目的 | 结果枚举 |
|-----------|---------|------|---------|
| `foundation_gate` | init-flow 生成 `foundation-review.md` 后 | 确认项目 north star、架构约束与 constitution 一致 | `passed \| failed \| blocked` |
| `feature_review_gate` | goal 写入 `feature.md` 后、architect 前 | 确认源需求具备 US/S/AC/GWT 追溯链 | `passed \| failed \| blocked` |
| `architect_gate` | goal 自动触发 architect 后 | 确认 `design.md` 已生成且决策合理 | `passed \| failed` |
| `tasks_gate` | plan 后 | 确认 `tasks.md` 可执行（ready task 具备 `Execution Block`） | `passed \| failed \| blocked` |
| `review_gate` | build-flow final review 后 | 确认任务实现、TDD receipt、设计一致性与代码质量已通过审查 | `passed \| failed \| blocked` |
| `ship_precheck_gate` | ship-flow | 由 `/bewater-ship` 基于 `validation_outcome`、freshness 与 release policy 合成；`--precheck-only` 只做审计检查 | `go \| no-go` |
| `quick_gate` | quick 流程 | 评估适用性与最小验证是否齐全 | `passed \| failed` |

---

## 状态转换图

```text
uninitialized --/bewater-init--> initialized
initialized --/bewater-goal(自动 architect)--> specified
specified --/bewater-plan + tasks_gate=passed--> planned
specified --/bewater-plan + tasks_gate=failed--> specified
planned --/bewater-build--> building
planned --/bewater-ship(existing implementation exception; promote to building)--> building
building --/bewater-ship --precheck-only--> building
building --/bewater-ship(precheck go + release intent)--> shipped
building --/bewater-ship(review_gate=passed, ship_precheck_gate=go, validate evidence checked)--> shipped
building --/bewater-ship(any required evidence missing)--> building
shipped --/bewater-learn--> shipped
```

### Quick Path

```text
initialized --/bewater-quick(minimal review + minimal validate)--> shipped
```

Quick 可以压缩公开状态，但不能跳过证据。

---

## `building -> shipped` 必要条件

必须同时满足：

1. `review_gate.status = passed`
2. `ship_precheck_gate.status = go`
3. `artifacts.validation_report_path` 已记录且文件存在
4. `validation-report.md` 已核验，且包含：
   - `release_decision: go`
   - `## E2E 测试结果`
   - `## Spec Consistency`
5. `gates.ship_precheck_gate.evidence_checked = true`

任一条件不满足：不得进入 `shipped`。

---

## 状态转换规则表

| 当前状态 | 触发条件 | 下一状态 | Gate | 输出产物 |
|---------|---------|---------|------|---------|
| `uninitialized` | `/bewater-init` | `initialized` | - | 项目级基础文档 |
| `initialized` | `/bewater-goal` | `specified` | `feature_review_gate` + `architect_gate` | `feature.md` + `feature-review.md` + `design.md` |
| `specified` | `/bewater-plan` | `planned` / `specified` | `tasks_gate` | `tasks.md` |
| `planned` | `/bewater-build` | `building` | `review_gate` | 代码 + 测试 + TDD receipts + `review-note.md` |
| `planned` | `/bewater-ship`（existing implementation 例外） | `building` | `ship_precheck_gate` | `validation-report.md` |
| `building` | `/bewater-ship --precheck-only` | `building` | `ship_precheck_gate` | `validation-report.md` |
| `building` | `/bewater-ship` | `shipped` / `building` | `ship_precheck_gate` | `validation-report.md` + `release-record.md` |
| `initialized` | `/bewater-quick` | `shipped` / `initialized` | `quick_gate` | 极简 `feature.md` + `review-note.md` + 最小验证证据 |
| `shipped` | `/bewater-learn` | `shipped` | - | 学习回写文档 |

---

## 失败处理

| 失败场景 | 处理方式 |
|---------|---------|
| `tasks_gate` 失败 | 保持 `specified`，修复后重跑 `/bewater-plan` |
| Builder 回执不完整 / 文件未落盘 | 保持 `building`，必要时重试 Builder 1 次 |
| Review 失败 | 保持 `building`，修复后继续 `/bewater-build` |
| Validate 证据不足 | 保持 `building`，补证据后重跑 `/bewater-ship` |
| Ship 证据核验失败 | 保持 `building`，禁止进入 `shipped` |
| 发布执行失败 | 保持 `building`，修复后重跑 `/bewater-ship` |

---

## 状态持久化字段契约

存储位置：`.bewater/state.json`

```json
{
  "version": "4.0.0",
  "current_state": "building",
  "previous_state": "planned",
  "feature_context": {
    "complexity_tier": "standard",
    "implementation_mode": "existing_complete",
    "existing_implementation_note": "代码已存在，仅补验证证据"
  },
  "internal_stage": "validating",
  "artifacts": {
    "feature_path": "docs/01-features/009-search-compare/feature.md",
    "design_path": "docs/01-features/009-search-compare/design.md",
    "tasks_path": "docs/01-features/009-search-compare/tasks.md",
    "review_note_path": "docs/01-features/009-search-compare/review-note.md",
    "validation_report_path": "docs/01-features/009-search-compare/validation-report.md"
  },
  "gates": {
    "review_gate": {
      "status": "passed",
      "blockers": [],
      "updated_at": "2026-04-21T10:00:00Z"
    },
    "ship_precheck_gate": {
      "status": "go",
      "blockers": [],
      "updated_at": "2026-04-21T18:00:00Z",
      "evidence_checked": true
    }
  }
}
```

> existing implementation 例外路径中，ship-flow 若从 `planned` 启动，must first move the feature into `building`，再生成验证证据。

Ownership rule: validate-flow writes `validation_outcome`; ship-flow writes `ship_precheck_gate`.

---

## 相关文档

- `command-boundaries.md` - 命令职责边界
- `risk-assessment.md` - 风险等级与验证深度
- `spec-consistency-checklist.md` - 规格闭环检查框架
