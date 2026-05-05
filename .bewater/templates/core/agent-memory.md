# Agent Memory Template

> BeWater Agent 持久化记忆 | 每个 Agent 维护自己的项目经验，跨功能积累

---

## 设计来源

借鉴 Claude Code `agentMemory.ts` 的三级记忆系统，简化为项目级单层记忆：

| 范围 | 路径 | 用途 |
|------|------|------|
| project | `.claude/agent-memory/{agent}/MEMORY.md` | 项目级 Agent 经验（入 VCS，团队共享） |

---

## 目录结构

```
.claude/
├── agent-memory/
│   ├── builder/
│   │   └── MEMORY.md       # Builder 的项目经验
│   ├── reviewer/
│   │   └── MEMORY.md       # Reviewer 的项目经验
│   ├── qa/
│   │   └── MEMORY.md       # QA 的项目经验
│   └── architect/
│       └── MEMORY.md       # Architect 的项目经验
```

---

## MEMORY.md 格式

```markdown
# {Agent Name} Memory

> 自动维护 | 由 /bewater-build（加载）和 /bewater-learn（更新）管理

## 项目技术偏好

- [记录项目特定的技术选择和偏好]

## 已知陷阱

- [记录在这个项目中踩过的坑]

## 架构约定

- [记录项目的架构模式和约束]

## 效果显著的策略

- [记录哪些开发/审查/测试策略效果最好]

## 需要避免的策略

- [记录哪些策略在这个项目中不适用]
```

---

## 使用方式

### Agent 启动时（加载记忆）

1. 检查 `.claude/agent-memory/{agent-name}/MEMORY.md` 是否存在
2. 如果存在，读取并应用其中的经验
3. 在实现/审查/测试中主动参考已知陷阱和偏好

### Agent 学习时（更新记忆）

1. 在 `/bewater-learn` 阶段，分析本次功能的经验
2. 提取 Agent 级别的经验（不是项目级别的 patterns/anti-patterns）
3. 追加或更新到对应的 MEMORY.md

### 与 patterns.md / anti-patterns.md 的关系

| 维度 | patterns.md / anti-patterns.md | agent-memory/MEMORY.md |
|------|-------------------------------|----------------------|
| 范围 | 项目级（所有 Agent 共享） | Agent 级（特定 Agent 专属） |
| 内容 | 通用模式和反模式 | 具体 Agent 的操作经验 |
| 更新时机 | `/bewater-learn` | `/bewater-learn` |
| 读者 | 所有 Agent | 特定 Agent |

---

## 与 Claude Code 的差异

- **简化为单层**：只保留 project 级别，不区分 user/local
- **Markdown 格式**：使用 Markdown 而非 JSON，方便人工审查
- **手动触发更新**：在 `/bewater-learn` 阶段更新，而非运行时自动写入
