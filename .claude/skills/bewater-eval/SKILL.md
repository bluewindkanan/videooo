---
name: bewater-eval
description: 执行 EDD 评估（默认 pre-ship，可选 post-ship 复盘），Use when 需要发布前证据评估或发布后复盘时
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
user-invocable: true
context: validation-report.md + release evidence + learning docs
effort: medium
---

# BeWater Eval

Optional utility for rerunning or reviewing AI behavior eval evidence and post-ship evaluation summaries. `/bewater-eval` is outside the main lifecycle, does not mutate delivery state, and does not replace `/bewater-validate`.

Use it to rerun planned AI behavior eval suites, summarize eval artifacts, compare scores against thresholds, or support `/bewater-learn` after ship.

## Lifecycle Position
- optional utility
- outside the main lifecycle
- 不改 delivery state
 - rerun planned AI behavior eval suites when needed (review-only)

## 模式

- `pre-ship`（默认）：发布前证据评估，辅助发布决策
- `post-ship`：发布后复盘评估

## 状态转换

- **前置**: `building` 或 `shipped` | **后置**: 状态不变（仅补充评估证据）| **下一步**: `/bewater-ship` 或 `/bewater-learn`

## 执行流程

### 步骤 1：读取成功指标

从 `docs/01-features/{编号}-{功能名}/feature.md` 读取成功指标。

### 步骤 2：收集实际数据

收集实际数据（测试结果、覆盖率、性能指标等）。

### 步骤 3：对比分析

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| ... | ... | ... | 达成/未达成 |

### 步骤 4：生成 edd-report.md

生成评估报告，写入功能目录或 learning 目录。

## 完成标准

- [ ] 已读取成功指标
- [ ] 已收集实际数据
- [ ] 已对比分析
- [ ] 已生成 edd-report.md
- [ ] 没有修改代码

## 约束

- 不能修改代码（只评估）
- 不能修改 feature.md（目标已框定）
- Must not create required AI eval assets during release validation; required assets belong to Build and are audited by Validate.

## 输出合约

```json
{
  "status": "passed|failed|blocked",
  "artifacts": {"report_path": "..."},
  "gate": {"name": "pre_ship_evidence", "status": "passed|failed|blocked|n/a"},
  "blockers": [],
  "next_action": "/bewater-ship | /bewater-learn",
  "mode": "pre-ship|post-ship",
  "evidence_score": "high|medium|low",
  "recommendation": "go|conditional|hold"
}
```

## 禁止事项

- 禁止修改代码（只评估）
- 禁止修改 feature.md（目标已框定）
