---
name: bewater-learn
description: 学习回写（从项目中提取可复用模式），Use when 功能已发布且需要总结经验教训时
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
user-invocable: true
context: validation-report.md + decision-log.md + learning docs
effort: medium
---

# BeWater Learn

学习回写（从项目中提取可复用模式）。

## Role Boundary
- runs after or at `shipped`
- captures learning artifacts only
- does not execute delivery transitions

## 状态转换

- **前置**: `shipped` | **后置**: `shipped`（学习已完成）| **下一步**: 下一个功能 `/bewater-goal`

## 执行流程

### 第 1 步：分析项目

分析项目中的：
- 代码模式
- 架构决策
- 测试策略
- 验证流程

### 第 2 步：识别可复用模式和失败教训

识别：
- 通用的代码模式
- 可复用的架构决策
- 有效的测试策略
- 成功的验证流程
- 失败的教训（anti-patterns）
  - AI behavior eval failures（e.g., hallucination, wrong_tool_use）that repeat across features should be captured as methodology feedback and exported to backlog.

### 第 3 步：生成学习文档

生成三个文档：
- `docs/02-learning/patterns.md` - 成功模式
- `docs/02-learning/anti-patterns.md` - 失败教训
- `docs/02-learning/retrospective.md` - 复盘记录

### 第 4 步：生成方法论反馈

对比本次项目体验与 BeWater 核心模板，生成 `docs/02-learning/methodology-feedback.md`，必须提取 plan-quality 相关信号：
- 哪些任务被过早标成 `ready`（ready too early）
- 哪些 `Execution Block` 字段经常缺失或失真
- 哪些 drift 属于模板缺陷、planner 问题、Builder 问题

### 结构化方法论 backlog

Learning artifacts must pass `.claude/scripts/check-learning-artifacts.py` before `/bewater-learn` reports success. Methodology backlog entries use statuses `open`, `accepted`, `rejected`, `planned`, and `done`.

生成 `docs/02-learning/methodology-backlog.json`。每个 `must / should / could` 反馈项必须包含：

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

`status` 生命周期：`open | accepted | rejected | planned | done`，初始值为 `open`。`source` 必须指向 `validation-report.md`、receipt、retrospective 或 methodology-feedback 中的证据。

### Lightweight Method Evaluation

Generate or update `docs/02-learning/evaluation-checklist.md`.

### AI Behavior Eval Learning

Capture repeated AI behavior eval failures when they indicate process flaws:

- hallucination
- unsafe_output
- ungrounded_claim
- wrong_tool_use
- missing eval strategy
- missing Eval Asset Map
- missing or stale `eval_evidence`
- escaped AI behavior bugs after ship

Repeated AI behavior eval failures should become `docs/02-learning/methodology-backlog.json` items when they imply a BeWater process change.

Capture:

- clarification rounds
- plan/build/validate retries
- validation no-go reasons
- missing evidence categories
- escaped bugs after ship
- user-visible discovery failures
- minimal usage path failures
- TDD receipt completeness
- cycle time from goal to ship precheck

Repeated blockers, missing evidence categories, and escaped bugs that imply a methodology flaw must be exported to `docs/02-learning/methodology-backlog.json`.

### 第 5 步：更新 Agent 记忆

为参与的 Agent 更新记忆（路径：`.claude/agent-memory/{agent-name}/MEMORY.md`）。

**5a. 识别参与的 Agent**：从 tasks.md TDD 记录、review notes、validation-report 确定哪些 Agent 参与了。**始终包含 Product Agent**（每个功能必经 goal 阶段）。如 agent-memory 目录不存在，先创建再写入。

**5b. 提取 Agent 特定经验**：
- Builder：发现了什么实现模式？遇到了什么陷阱？什么项目偏好？
- Reviewer：捕获了什么问题？什么误报？
- QA：什么测试模式有效？什么难以测试？性能基线数据？
- Architect：什么架构决策？什么约束？
- Product：什么业务领域知识？什么需求模式？什么范围控制经验？

**5c. 写入 MEMORY.md**：读取现有 `.claude/agent-memory/{agent}/MEMORY.md`，合并新经验，写回。文件不超过 50 行。

**5d. 生成 Agent .md 拟议修改**：从提取的经验中生成对 Agent .md 文件的改进建议，写入 `methodology-feedback.md` 的"拟议 Agent 改进"章节。

### 第 6 步：建议回写

将 methodology-feedback.md 中的改进项按 `must / should / could` 分组输出。每项必须附带：
- 具体目标文件
- 建议变更
- 来自 `validation-report.md` 或 receipt 的证据

### 第 7 步：更新状态

更新 `.bewater/state.json`，标记学习已完成：

```json
{
  "learned_at": "[ISO日期]"
}
```

状态保持为 `shipped`，但标记学习阶段已完成。

## 完成标准

- [ ] 已分析项目代码模式、架构决策、测试策略、验证流程
- [ ] 已识别可复用模式和失败教训
- [ ] 已生成 `docs/02-learning/patterns.md`
- [ ] 已生成 `docs/02-learning/anti-patterns.md`（**必须生成，不可跳过**）
- [ ] 已生成 `docs/02-learning/retrospective.md`
- [ ] 已生成 `docs/02-learning/evaluation-checklist.md`
- [ ] 已生成 `docs/02-learning/methodology-feedback.md`（**必须自动填充，不可留空**）
- [ ] 已更新参与 Agent 的 `.claude/agent-memory/{agent}/MEMORY.md`
- [ ] 已在 methodology-feedback.md 生成 Agent .md 拟议修改建议
- [ ] 已建议回写到 BeWater 方法论
- [ ] 没有修改项目代码
