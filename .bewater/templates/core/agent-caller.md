# Agent 调用标准规范

> **版本**: 1.0.0
> **目的**: 统一 BeWater 方法论中 Agent 调用的格式、流程和错误处理
> **适用范围**: 所有需要调用子代理的 Skill

---

## 核心原则

1. **统一格式**: 所有 Agent 调用使用相同的参数结构和 prompt 模板
2. **上下文优先**: 子代理通过 `context-manifest.md` 继承上下文
3. **返回契约**: 子代理返回 JSON 摘要，详细内容写入文件
4. **错误处理**: 必须处理权限拒绝、超时、返回格式错误等情况
5. **完成即释放**: 子代理完成任务后立即释放，不保留上下文
6. **上下文预算**: 调度前估算文档总 token，超过 60% 窗口时用摘要替代

Agent outputs are recommendations. The caller Skill owns state mutation and gate persistence. If an Agent returns `recommended_gate_status`, the Skill must decide whether and how to persist the canonical gate.

Default public path: `goal -> plan -> build -> validate -> ship`
Public validation path: `goal -> plan -> build -> validate -> ship`
Shared freshness checker: `.claude/scripts/check-gate-freshness.py`

---

## 标准调用格式

### 基本结构

```markdown
使用 Agent tool，参数如下：
- subagent_type: "[优先使用项目内专用类型；宿主不支持时回退通用类型]"
- description: "[简短描述，5 词以内]"
- prompt: |
  ## 你的角色
  你是 [Agent Name]...

  ## 上下文继承
  使用 Read tool 读取 `.bewater/context-manifest.md`...

  ## 任务
  [具体任务描述]

  ## 输出合约
  [JSON 格式要求]
```

### subagent_type 对照表

| Agent 角色 | 首选 subagent_type | 宿主不支持自定义类型时 | 说明 |
|------------|--------------------|------------------------|------|
| Architect | `architect` | 使用宿主默认通用类型，并在 prompt 中读取 `.claude/agents/architect.md` | 架构设计、技术选型 |
| Builder | `builder` | 使用宿主默认通用类型，并在 prompt 中读取 `.claude/agents/builder.md` | 代码实现、测试编写 |
| Plan（内置） | `Plan` | 使用宿主默认通用类型，并在 prompt 中显式写明 Planning Agent 角色 | 任务拆解、依赖分析（用于 `/bewater-plan`） |
| QA | `qa` | 使用宿主默认通用类型，并在 prompt 中读取 `.claude/agents/qa.md` | 场景验证、接口验证（含安全与性能维度） |
| Reviewer | `reviewer` | 使用宿主默认通用类型，并在 prompt 中读取 `.claude/agents/reviewer.md` | 代码审查、质量检查 |
| Product | `product` | 使用宿主默认通用类型，并在 prompt 中读取 `.claude/agents/product.md` | 需求澄清、目标框定、范围挑战（用于 `/bewater-goal`） |

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `subagent_type` | string | ✅ | 优先使用上表中的专用类型；若宿主只支持通用 agent type，则回退到通用类型，但不得省略角色定义文件 |
| `description` | string | ✅ | 简短描述，5 词以内 |
| `prompt` | string | ✅ | 详细任务描述，遵循下文模板 |

---

## Prompt 模板

### 必需章节

所有 Agent 调用的 prompt 必须包含以下章节：

```markdown
## 你的角色
[Agent 名称] 和 [核心职责]

## 上下文继承
使用 Read tool 读取 `.bewater/context-manifest.md`，获取：
- 当前功能的文档索引
- 项目级文档索引
- 前序阶段摘要
- Agent 记忆路径

## 启动步骤
1. 使用 Read tool 读取 `.claude/agents/[agent-name].md`，理解角色定义
2. **加载 Agent 记忆**：如果 `.claude/agent-memory/[agent-name]/MEMORY.md` 存在，读取并应用
3. 通过 manifest 中的文档索引，按需读取以下文档：
   - [列出需要读取的文档]

### 上下文预算（调度前必查）

调度 Agent 前，读取 manifest 的 est_tokens 列，求和：
- **< 60% 窗口（~8000 token）**：正常调度，传递完整文档路径
- **> 60% 窗口**：只传递 Phase Summaries + 核心文档（feature.md + tasks.md），跳过 architecture.md 等次要文档

## 任务
[具体任务描述，可分多级章节]

## 输出合约（强制）
所有详细输出使用 Write tool 写入 [路径]。
完成后，只输出以下 JSON 摘要（一行）：
{"status":"passed|failed","key":"value"}

**禁止事项**：
- 不得在 JSON 输出之外返回详细内容
```

---

## 权限拒绝处理

### 检测方式

Agent tool 返回错误消息中包含 "user denied" 或 "permission denied"。

### 处理策略

| 场景 | 处理方式 |
|------|---------|
| **可选 Agent 被拒绝** | 记录警告，继续执行 |
| **必需 Agent 被拒绝** | 暂停并提示用户，提供重试选项 |

### 实现模板

```markdown
## 权限拒绝处理

如果用户拒绝 Agent tool 调用：

**必需 Agent（如 Reviewer for Critical/High 风险）**：
```
⚠️ Agent 调用被用户拒绝

当前任务需要 [Agent Name] 审查才能继续。
请选择：
1. 重新请求授权
2. 跳过（记录技术债务）
3. 取消操作

输入选项 [1/2/3]:
```

**可选 Agent（如 Reviewer for Medium/Low 风险）**：
```
⚠️ Agent 调用被用户拒绝（可选任务）

将继续执行，但会记录为技术债务。
```
```

---

## 并行调用规范

### 单消息多调用

使用 Agent tool 并行调用多个 Agent 时，必须在**同一条消息**中发起所有调用：

```markdown
同时启动 QA Agent 和 Security/Performance 检查（由 QA 单 Agent 执行）
```

### 部分成功处理

| 场景 | 处理方式 |
|------|---------|
| 全部成功 | 合并所有结果 |
| 部分失败 | 记录失败项，合并成功结果，标记"部分完成" |
| 全部失败 | 标记"验证失败"，提供详细错误信息 |

### 实现模板

```markdown
## 并行调用失败处理

等待两个 Agent 都返回结果后：

1. **检查返回状态**：
   - 两个都成功 → 合并结果
   - 一个成功一个失败 → 部分完成，记录失败项
   - 两个都失败 → 标记失败

2. **输出格式**：
   ```json
   {
     "overall_status": "passed|partial|failed",
     "dimensions": {
       "functional": {"status": "passed|failed", ...},
       "security": {"status": "passed|failed", ...},
       "performance": {"status": "passed|failed", ...}
     }
   }
   ```
```

---

## 输出契约规范

### JSON 摘要格式

子代理必须返回 JSON 摘要，包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | ✅ | `passed` / `failed` / `partial` |
| `blockers` | array | ✅ | 阻断项列表 |
| `[具体字段]` | any | - | 根据任务类型添加 |

### 示例

```json
{
  "status": "passed",
  "tasks_completed": ["1.1", "1.2"],
  "test_coverage": 87,
  "blockers": []
}
```

---

## 上下文管理

### 读取顺序

子代理必须按以下顺序读取文档：

1. `.bewater/context-manifest.md` - 获取文档索引
2. `.claude/agents/[agent-name].md` - 理解角色定义
3. `.claude/agent-memory/[agent-name]/MEMORY.md` - 加载记忆（如存在）
4. 具体任务文档（通过 manifest 索引）

### 写入规则

- 详细输出使用 Write tool 写入文件
- JSON 摘要通过返回值传递
- 禁止在 JSON 输出之外返回详细内容

---

## 常见场景

### 场景 1: Builder Agent 调用

```markdown
使用 Agent tool，参数如下：
- subagent_type: "builder"
- description: "TDD implementation for feature {编号}"
- prompt: |
  ## 你的角色
  你是 Builder Agent，负责以 TDD 方式实现功能 {编号}。

  ## 上下文继承
  使用 Read tool 读取 `.bewater/context-manifest.md`...

  ## 启动步骤
  1. 读取 `.claude/agents/builder.md`
  2. 加载 Agent 记忆（如存在）
  3. 读取 feature.md 和 tasks.md

  ## 任务
  [TDD 实现任务]

  ## 输出合约（强制）
  {"status":"success|blocked","tasks_completed":[...],"blockers":[...]}
```

> 如果当前宿主不支持 `builder` 这类项目内专用类型，则改用宿主默认通用类型，并保留同一份 prompt 与 `.claude/agents/builder.md` 读取步骤。

### 场景 2: Reviewer Agent 调用

```markdown
使用 Agent tool，参数如下：
- subagent_type: "reviewer"
- description: "Review for feature {编号}"
- prompt: |
  ## 你的角色
  你是 Reviewer Agent，负责代码审查。

  ## 上下文继承
  使用 Read tool 读取 `.bewater/context-manifest.md`...

  ## 启动步骤
  1. 读取 `.claude/agents/reviewer.md`
  2. 加载 Agent 记忆（如存在）
  3. 读取 feature.md 和 tasks.md

  ## 任务
  [审查任务]

  ## 输出合约（强制）
  {"status":"passed|needs_fix","blockers":[...],"suggestions":[...]}
```

> 如果当前宿主不支持 `reviewer` 这类项目内专用类型，则改用宿主默认通用类型，并保留同一份 prompt 与 `.claude/agents/reviewer.md` 读取步骤。

### 场景 3: 并行验证调用

```markdown
启动 QA Agent 执行功能/安全/性能验证（单 Agent 覆盖全部维度）

[QA Agent 调用...]
```

---

## 错误恢复

### 错误分类

| 错误类型 | 处理策略 | 示例 |
|---------|---------|------|
| 权限拒绝 | 提示用户重新授权或跳过 | Agent tool 被拒绝 |
| 文档缺失 | 自动创建模板或提示 | feature.md 不存在 |
| 依赖失败 | 标记阻塞，跳过非关键步骤 | API 调用失败 |
| 超时 | 重试 1 次，然后标记超时 | Agent 执行 > 5 分钟 |
| 返回格式错误 | 记录错误，使用默认值 | JSON 解析失败 |

---

## 检查清单

Agent 调用前：
- [ ] 已准备完整的 prompt（包含所有必需章节）
- [ ] 已明确子代理角色
- [ ] 已指定输出契约
- [ ] 已准备权限拒绝处理方案

Agent 调用后：
- [ ] 已处理返回值
- [ ] 已检查 status 字段
- [ ] 已读取详细输出文件（如有）
- [ ] 已更新 context-manifest.md 和 state.json

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-04-01 | 初始版本 |
