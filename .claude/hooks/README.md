# BeWater Hooks（本地/CI 质量约束）

> 目标：在不增加流程负担的前提下，把 BeWater 的风险分级质量策略变成”可执行阻断”。

## 自动注册机制

运行 `install.sh` 时，会自动将 BeWater hooks 注册到项目的 `.claude/settings.local.json`：

```json
{
  “hooks”: {
    “PreToolUse”: [
      {
        “matcher”: “tool == \”Bash\” && tool_input.command matches \”(npm|yarn|pnpm|bun) (test|run|build|start)\””,
        “hooks”: [{ “type”: “command”, “command”: “bash \”$CLAUDE_PROJECT_DIR/.claude/hooks/pre-build-doc-check.sh\”” }]
      },
      {
        “matcher”: “tool == \”Bash\” && tool_input.command matches \”git commit\””,
        “hooks”: [{ “type”: “command”, “command”: “bash \”$CLAUDE_PROJECT_DIR/.claude/hooks/pre-commit-tdd-check.sh\”” }]
      }
    ]
  }
}
```

**注意**：
- `install.sh` 会把 hooks 安装到目标项目的 `.claude/hooks/`
- hooks command 里的 `$CLAUDE_PROJECT_DIR` 指向目标项目根，因此命令路径应写成 `$CLAUDE_PROJECT_DIR/.claude/hooks/...`
- 配置写入 `settings.local.json`（本地配置，不进入版本控制）
- 不影响全局配置（`~/.claude/settings.json`）

**跳过自动注册**：`./install.sh --skip-hooks-config`

## Hook 列表

| Hook | 触发时机 | 检查项 | 阻断条件 |
|------|----------|--------|----------|
| `pre-build-doc-check` | npm/yarn test/build 前 | 文档完整性、追溯链 | 缺失关键文档时警告 |
| `pre-commit-tdd-check` | git commit 前 | TDD 合规、风险↔质量策略 | 有阻断项直接退出 |
| `pre-push` / CI | 推送/CI 前 | 验证报告阻断项、安全/性能红灯 | 有阻断项直接退出 |
| `checkAgentToolCompliance` | CI / pre-commit | Agent 工具声明合规性 | 工具不在白名单、tools 与 disallowedTools 重叠时阻断 |

## 核心检查规则

1) **风险分级 TDD/覆盖率/Review 对齐**
   - 读取 `docs/01-features/{编号}-{功能名}/tasks.md` 里的任务风险等级。
   - Critical → 覆盖率≥80%、TDD=强制、Code Review=必须
   - High → 覆盖率≥70%、TDD=强制、Code Review=必须
   - Medium → 覆盖率≥60%、TDD=强制、Code Review=抽检
   - Low → 覆盖率≥50%、TDD=强制、Code Review=允许轻量
   - 若 `quality strategy` 未填写、TDD 未标为强制，或覆盖率/Review 低于等级要求 → 阻断。

2) **验证阻断项**  
   - 读取 `docs/01-features/{编号}-{功能名}/validation-report.md`。  
   - 若存在阻断项（Blockers 表任一未完成）或发布决策为“不批准/有条件未满足” → 阻断。

3) **追溯链完整性**  
   - feature.md / tasks.md / validation-report.md 必须存在。
   - tasks.md 中的任务必须填写验收标准；缺失则警告（默认阻断以稳为主）。

## 安装（本地可选）

```bash
# 安装 pre-commit hook
ln -sf ../../hooks/scripts/bewater-hook.js .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## CI 用法示例（pseudo）

```yaml
steps:
  - uses: actions/checkout@v4
  - run: node 05-implementations/bewater/hooks/scripts/bewater-hook.js --mode ci
```

## 设计取舍

- 仅依赖 Node，无外部包，便于在任意仓库/CI 运行。  
- 以“阻断安全”为默认（宁可多阻断，避免低质发布）。  
- 不强行跑测试；只检查声明与产物的内在一致性。

## Gate Freshness Early Warning

`check-gate-freshness.py` is an early-warning checker shared by flows, status, next, and CI wrappers.
It reports potential stale gates from digest or artifact drift, but it is not the authoritative flow decider.
