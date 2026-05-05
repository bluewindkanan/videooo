# Context Manifest

> 轻量级索引；只用于定位文档与复用摘要，不承担状态判断。

## 权威性
- 状态、gate、next_command：只读 `.bewater/state.json`
- `context-manifest.md`：摘要索引
- `session-context.md`：会话缓存
- 任意冲突：以 `state.json` 为准

## 当前功能

| 字段 | 值 |
|------|-----|
| 功能编号 | 001 |
| 功能名称 | 知识分享视频任务骨架（任务 / 步骤 / 产物） |
| 状态镜像（from state.json） | specified |

## 文档索引

| 文档 | 路径 | est_tokens |
|------|------|-----------|
| feature.md | docs/01-features/{编号}-{功能名}/feature.md | ~800 |
| tasks.md | docs/01-features/{编号}-{功能名}/tasks.md | ~1200 |
| architecture.md | docs/01-features/{编号}-{功能名}/architecture.md（按需） | ~600 |
| validation-report.md | docs/01-features/{编号}-{功能名}/validation-report.md | ~1000 |

## 项目级文档

| 文档 | 路径 |
|------|------|
| 全局架构 | docs/00-project/architecture.md |
| 项目宪法 | docs/00-project/constitution.md |
| 成功模式 | docs/02-learning/patterns.md |
| 失败教训 | docs/02-learning/anti-patterns.md |
| 方法评估清单 | docs/02-learning/evaluation-checklist.md |

## Agent 记忆

| Agent | 路径 |
|-------|------|
| Builder | .claude/agent-memory/builder/MEMORY.md |
| Reviewer | .claude/agent-memory/reviewer/MEMORY.md |
| QA | .claude/agent-memory/qa/MEMORY.md |
| Architect | .claude/agent-memory/architect/MEMORY.md |
| Product | .claude/agent-memory/product/MEMORY.md |

## Phase Summaries

> 仅供快速理解，不得作为 gate 或状态推进依据。

- [YYYY-MM-DD HH:MM] Goal: {一句话目标摘要}
- [YYYY-MM-DD HH:MM] Architect: {设计结论或跳过原因}
- [YYYY-MM-DD HH:MM] Plan: {N} tasks, {M} stages
- [YYYY-MM-DD HH:MM] Build: {X}/{Y} complete, {关键回执}
- [YYYY-MM-DD HH:MM] Review: {passed|blocked}, {N} blockers
- [YYYY-MM-DD HH:MM] Validate: {go|no-go}, {关键证据}
- [YYYY-MM-DD HH:MM] Ship: {结果摘要}

## 使用方式
1. 先读 manifest 定位文档与前序摘要。
2. 需要判断状态、gate、是否可推进时，重新读取 `.bewater/state.json`。
3. 子代理按需读取 feature/design/tasks/validation-report，不默认全量重读。
4. 执行结束后只更新摘要，不在本文件写状态结论。

## 上下文预算协议
- 优先传 manifest 路径与明确任务，不重复粘贴完整文档。
- 上下文紧张时优先读 Phase Summaries，再按需补读原文档。
- 文档过大时优先读取当前阶段必需文件。  
