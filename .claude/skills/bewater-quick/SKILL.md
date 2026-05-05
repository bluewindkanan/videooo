---
name: bewater-quick
description: 低风险小改动快捷命令（跳过 plan，仍要求最小验证）
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
user-invocable: true
context: low-risk change scope + minimal validation + state.json
effort: medium
---

# BeWater Quick

小改动快捷路径。只处理低风险变更，可以跳过 `plan`，但不能跳过最小验证。

## Quick Route Rules
- may set `runtime.route_mode = quick`
- still requires fresh `review_gate = passed`
- still requires validation evidence and final `ship_precheck_gate = go`
- may use `.claude/scripts/bewater-gate-evaluate.py` for read-only minimum validation and risk checks before shipping

## Trigger

- 当变更是 CSS/样式调整、文案/内容修改、小重构、配置微调、单文件 bug 修复时使用。

## State

- 前置：`initialized`
- 后置：`shipped` 或 `initialized`
- 下一步：`/bewater-learn`

## Gate（强制）

1. **适用性 Gate**：必须评估变更是否适合 Quick 流程，不适合则拒绝
2. **轻量 Review Gate**：必须落盘 `review-note.md`
3. **最小验证 Gate**：必须落盘轻量 `validation-report.md`
4. **构建 Gate**：`npm run build` 必须通过
5. **Smoke Gate**：应用必须正常启动或完成等效 smoke check

## 适用性评估

### 适合 Quick

- CSS/样式调整
- 文案/内容修改
- 小重构
- 配置微调
- 单文件低风险 bug 修复

### 不适合 Quick

- 新页面/新组件
- 多模块联动
- 安全/认证相关
- 数据模型变更
- API 接口变更
- 不确定的变更

## Quick Path Blocked Categories

`/bewater-quick` must not be used when the requested change involves:

- data migration
- security permission changes
- payment or billing behavior
- production release automation
- cross-module refactor
- irreversible operation

If any category matches, use the standard `goal -> plan -> build -> validate -> ship` path.

## 执行步骤

1. 接收一句话变更描述
2. 判断是否适合 Quick
   - 不适合：提示改走 `/bewater-goal`
3. 生成极简 `feature.md`
   - 自动设置 `risk_level: low`
4. 调用 Builder 子代理：读取 `.claude/agents/builder.md`
5. 写入轻量 `review-note.md`
6. 运行最小验证：
   - `npm run build`
   - smoke check
7. 生成轻量 `validation-report.md`
   - 必须包含执行命令
   - 必须包含结果摘要
   - 必须包含 `release_decision: go|no-go`
8. 仅在最小验证通过后写入 `shipped`

## 状态路径

```text
initialized → shipped
```

> 说明：这是压缩后的公开状态表现。Quick 内部仍要完成轻量 review 与最小验证。

## 状态变更指令（强制）

```json
{
  "current_state": "shipped",
  "shipped_at": "[ISO日期]",
  "artifacts": {
    "feature_path": "docs/01-features/[编号]-[名称]/feature.md",
    "review_note_path": "docs/01-features/[编号]-[名称]/review-note.md",
    "validation_report_path": "docs/01-features/[编号]-[名称]/validation-report.md"
  },
  "gates": {
    "quick_gate": {"status": "passed|failed", "blockers": [], "updated_at": "[ISO时间]"},
    "review_gate": {"status": "passed", "blockers": [], "updated_at": "[ISO时间]"},
    "ship_precheck_gate": {"status": "go|no-go", "blockers": [], "updated_at": "[ISO时间]", "evidence_checked": true}
  },
  "next_command": "/bewater-learn"
}
```

## 禁止事项

- 禁止用于不适合的变更类型
- 禁止跳过最小验证
- 禁止无 `validation-report.md` 进入 `shipped`
- 禁止用口头说明替代验证证据

## 输出合约

```json
{
  "status": "passed|failed|rejected",
  "artifacts": {
    "feature_path": "...",
    "review_note_path": "...",
    "validation_report_path": "...",
    "files_changed": ["..."]
  },
  "gate": {"name": "quick_gate", "status": "passed|failed"},
  "blockers": [],
  "next_action": "/bewater-learn",
  "rejection_reason": "null | 变更不适合 Quick 流程"
}
```
