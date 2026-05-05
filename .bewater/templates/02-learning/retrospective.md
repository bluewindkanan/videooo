# Retrospective（复盘记录）

> **用途**: 项目/功能完成后的复盘记录，总结经验教训
> **生成命令**: `/bewater-learn`

## 基本信息

**复盘时间**: YYYY-MM-DD
**功能/项目**: [名称]
**参与人员**: [姓名列表]
**时间跨度**: [开始日期] ~ [结束日期]
**总工作量**: [X] 人天

## Structured Summary

The JSON block below must remain compatible with `.bewater/contracts/retrospective.schema.json`.

```json
{
  "feature": "[名称]",
  "completed_at": "YYYY-MM-DD",
  "outcome": "completed|partial|blocked",
  "learnings": [],
  "action_items": []
}
```

## 目标回顾

**原始目标**:
<!-- 从 feature.md 复制 -->

**实际完成**:
<!-- 实际完成了什么？ -->

**目标达成度**: [X]%

**未完成部分**:
- [ ] 未完成项 1 - 原因: [...]
- [ ] 未完成项 2 - 原因: [...]

## 数据回顾

### 工作量统计

| 阶段 | 预估工作量 | 实际工作量 | 偏差 |
|------|-----------|-----------|------|
| Goal Framing | 2h | 1.5h | -25% |
| Planning | 4h | 6h | +50% |
| Building | 20h | 25h | +25% |
| Validation | 4h | 3h | -25% |
| Learning | 2h | 2h | 0% |
| **总计** | **32h** | **37.5h** | **+17%** |

### 质量指标

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 测试覆盖率 | 80% | 85% | ✅ |
| Bug 数量 | < 5 | 3 | ✅ |
| 性能 (p95) | < 300ms | 280ms | ✅ |
| 代码审查通过率 | 100% | 100% | ✅ |

### Method Evaluation Metrics

| Metric | Value | Evidence Ref | Notes |
|--------|-------|--------------|-------|
| clarification rounds | [number] | `feature.md#intent_review` | [notes] |
| plan/build/validate retries | [number] | `.bewater/state.json#runtime.retry_counters` | [notes] |
| validation no-go reasons | [list] | `validation-report.md#Blockers` | [notes] |
| missing evidence categories | [list] | `validation-report.md#Drift Summary` | [notes] |
| escaped bugs after ship | [number/list] | `retrospective.md#What Needs Improvement` | [notes] |
| user-visible discovery failures | [number/list] | `validation-report.md#Discoverability & Usage Path` | [notes] |
| minimal usage path failures | [number/list] | `validation-report.md#Discoverability & Usage Path` | [notes] |
| TDD receipt completeness | [percent/status] | `receipts.json` | [notes] |
| cycle time from goal to ship precheck | [duration] | `.bewater/state.json#state_history` | [notes] |

### AI 努力压缩比

| 任务类型 | 人类团队预估 | BeWater + AI 实际 | 压缩比 |
|---------|-------------|------------------|--------|
| 脚手架代码 | 2 天 | 15 分钟 | high |
| 功能实现 | 1 周 | 25 小时 | ~13x |
| 测试编写 | 1 天 | 3 小时 | ~2.7x |
| 文档编写 | 4 小时 | 1 小时 | ~4x |

## 做得好的地方（What Went Well）

### 1. [亮点 1]

**描述**:
<!-- 具体描述做得好的地方 -->

**为什么做得好**:
<!-- 分析成功的原因 -->

**可复用性**:
<!-- 这个经验是否可以复用到其他项目？ -->
- [ ] 已记录到 patterns.md

---

### 2. [亮点 2]

**描述**:

**为什么做得好**:

**可复用性**:
- [ ] 已记录到 patterns.md

---

## 需要改进的地方（What Needs Improvement）

### 1. [问题 1]

**描述**:
<!-- 具体描述遇到的问题 -->

**影响**:
<!-- 这个问题带来了什么影响？ -->

**根本原因**:
<!-- 为什么会出现这个问题？ -->

**改进措施**:
<!-- 下次如何避免？ -->
- [ ] 措施 1
- [ ] 措施 2

**可复用性**:
- [ ] 已记录到 anti-patterns.md

---

### 2. [问题 2]

**描述**:

**影响**:

**根本原因**:

**改进措施**:
- [ ] 措施 1
- [ ] 措施 2

**可复用性**:
- [ ] 已记录到 anti-patterns.md

---

## 意外发现（Surprises）

### 1. [意外 1]

**描述**:
<!-- 有什么意外的发现？ -->

**影响**:
<!-- 这个发现对项目有什么影响？ -->

**后续行动**:
<!-- 需要采取什么行动？ -->

---

## 行动项（Action Items）

| 编号 | 行动项 | 负责人 | 截止日期 | 状态 |
|------|--------|--------|---------|------|
| A1 | [行动项 1] | [姓名] | YYYY-MM-DD | ⏳ |
| A2 | [行动项 2] | [姓名] | YYYY-MM-DD | ⏳ |

## 知识沉淀

### 新增 Patterns
- [ ] Pattern [P00X]: [名称] - 已添加到 patterns.md

### 新增 Anti-Patterns
- [ ] Anti-Pattern [AP00X]: [名称] - 已添加到 anti-patterns.md

### 新增回归测试
- [ ] `test_case_1` - 防止 [AP00X] 再次发生
- [ ] `test_case_2` - 防止 [AP00Y] 再次发生

## 团队反馈

### 成员 1: [姓名]

**最满意的地方**:

**最不满意的地方**:

**建议**:

---

### 成员 2: [姓名]

**最满意的地方**:

**最不满意的地方**:

**建议**:

---

## 下一步计划

**短期计划**（1-2 周）:
- [ ] 计划 1
- [ ] 计划 2

**中期计划**（1-3 月）:
- [ ] 计划 1
- [ ] 计划 2

**长期计划**（3+ 月）:
- [ ] 计划 1
- [ ] 计划 2

---

### Execution Contract Drift Notes

- [ ] 哪些任务被过早标成 `ready`
- [ ] 哪些 `Execution Block` 字段在执行中失真
- [ ] 哪些 `Done definition` 或 `Verify commands` 无法审计

## 方法论反馈

> 本章节为 BeWater 方法论自进化的核心输入。详细内容见 `methodology-feedback.md`。

### 对 BeWater 方法论的改进建议

| # | 目标文件 | 建议变更 | 优先级 | 状态 |
|---|----------|----------|--------|------|
| 1 | | | P1 | ⏳ |

> 详细改进项列表和追踪状态见 [methodology-feedback.md](./methodology-feedback.md)
