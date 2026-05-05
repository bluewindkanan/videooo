# SHARED_EXECUTION_TEMPLATE (Reference Only)

> 仅作模板参考，不替代各 SKILL 的自包含步骤。

## Minimal Skill Skeleton

1. Trigger：何时使用
2. State：前置/后置状态（检查 `.bewater/state.json` 的 `current_state`）
3. Gate：强制门禁与阻断逻辑
4. Agent Dispatch：读取 `.claude/agents/<role>.md`（含 `base: SHARED_AGENT_BASE.md` 公共协议）+ 输入输出映射
5. Output Contract：JSON（`status: passed|failed|blocked`，决策 `go|no-go`）
6. 禁止事项：明确不可执行动作

## Authority Rule

- flows own lifecycle progression
- agents own role judgment
- capability packs own reusable methods only
- deterministic scripts own machine checks

## State Check Pattern

```
1. 读取 .bewater/state.json
2. 检查 current_state 满足前置条件
3. 执行命令逻辑
4. 更新 current_state 为后置状态
```

## Agent Prompt Simplification Pattern

- 角色定义：`读取 .claude/agents/<role>.md`
- 输入文档：列出最小必需文档路径
- 执行边界：列出必须做与禁止做
- 输出：仅 JSON 摘要，字段遵循 skill 本地合约

## State Change Template

所有 SKILL 的状态变更统一写入 `.bewater/state.json`：

```json
{
  "current_state": "新状态",
  "gates": { "...": { "status": "..." } },
  "next_command": "..."
}
```

同步更新 `.bewater/context-manifest.md` 的功能索引和 Phase Summaries。
