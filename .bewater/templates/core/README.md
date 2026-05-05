# 核心概念

> BeWater 方法论的核心概念和架构设计

## 文档列表

### 核心架构
- [command-boundaries.md](command-boundaries.md) - 命令职责边界
- [state-machine.md](state-machine.md) - 状态机设计
- [context-manifest.md](context-manifest.md) - 上下文索引机制
- [agent-memory.md](agent-memory.md) - Agent 记忆系统

### 执行规范
- [agent-caller.md](agent-caller.md) - Agent 调用标准规范
- [error-handling.md](error-handling.md) - 错误处理策略
- [environment-checklist.md](environment-checklist.md) - 环境检查清单
- [state.md](state.md) - 状态持久化字段契约说明
- [state-template.json](state-template.json) - 可解析状态模板

### 工作流程
- [WORKFLOW.md](../../WORKFLOW.md) - 工作流程详解

## 概述

BeWater 采用 **Skills + Agents 两层架构**，通过文档工件串联整个开发过程。

Version: 4.0.0
Published: 2026-04-28
Public path: `init -> goal -> plan -> build -> validate -> ship`
Public validation path: `goal -> plan -> build -> validate -> ship`

### 核心架构

```
Skills 层（用户入口）
  ↓
Agents 层（执行者）
  ↓
文档工件（追溯链）
```

### 9 阶段工作流

```
Init → Goal → Architecture → Plan → Build → Review → Validate → Ship → Learn
```

查看 [WORKFLOW.md](../../WORKFLOW.md) 了解详细流程。
