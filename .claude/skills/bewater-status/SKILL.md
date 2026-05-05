---
name: bewater-status
description: 查看 BeWater 项目当前状态，Use when 需要查看项目状态、了解当前进度或查看验证结果时
allowed-tools: [Read, Glob, Grep, Bash]
user-invocable: true
context: state.json + artifact paths + gate statuses
effort: small
---

# BeWater Status

查看 BeWater 项目当前状态。

## Summary Fields
- current public state
- active flow
- runtime subphase
- gate highlights
- stale gates
- documentation freshness
- produced or updated artifacts
- recommended next action

When available, `/bewater-status` may use `.claude/scripts/bewater-gate-evaluate.py` for read-only semantic gate verdicts. The evaluator does not write lifecycle state or gates.
When `feature.md` contains `last_verified_commit` and `implementation_paths`, `/bewater-status` should treat feature docs as historical delivery claims and report `docs_may_be_stale` if implementation paths changed after the verified commit.

## Plain-language next action

Default output starts with a non-technical summary:

```text
Recommended next action: {plain-language action}
Why this is next: {short reason based on current_state, validation_outcome, or release policy}
Evidence to review:
- {artifact path or none}

Technical details are available on request.
```

Then include the detailed state/gate section below when the user asks for details or when a blocker requires audit evidence.

## 执行流程

### 第 1 步：读取项目文件

**优先读取 context-manifest.md**（轻量级索引）：
- `.bewater/context-manifest.md` — 功能索引 + 阶段摘要
- `.bewater/state.json` — 状态持久化

**仅在需要详情时**，按需读取完整文档：
- `docs/01-features/{编号}-{功能名}/feature.md`
- `docs/01-features/{编号}-{功能名}/tasks.md`
- `docs/01-features/{编号}-{功能名}/validation-report.md`

项目级文档：
- `docs/00-project/architecture.md`

### 第 2 步：分析状态

从 state.json 读取当前状态：
- `uninitialized` - 项目未初始化
- `initialized` - 项目已初始化（含 constitution）
- `specified` - 目标已定义（含研究和架构评估）
- `planned` - 任务已规划
- `building` - 开发中
- `shipped` - 已发布

### 第 3 步：显示状态摘要

```
BeWater 项目状态

项目: {project}
状态: {current_state}
当前功能: {current_feature}

Gates:
  tasks_gate: {status}
  ship_precheck_gate: {status}

validation evidence:
  validation_report_path: {path}
  validation_outcome.classification: {ready_for_precheck|evidence_incomplete_or_stale|implementation_gap|spec_package_drift|goal_scope_contradiction|unknown}
  validation_outcome.release_decision: {go|no-go|unknown}
  validate_command: /bewater-validate
  freshness: {fresh|stale|unknown}

documentation freshness:
  lifecycle_status: {active|superseded|partially_superseded|unknown}
  last_verified_commit: {sha|null}
  docs_freshness: {fresh|docs_may_be_stale|unknown}
  stale_reason: {implementation path changed after last_verified_commit|N/A}

已发布功能: {shipped_features}

下一步: {next_command}
```

## Release Boundary Status

Read `.bewater/release.json`; if missing, report local default.

Status output must include:
- `release_boundary`
- Enabled adapters
- `will_commit`
- `will_push`
- `will_run_script`
- whether irreversible acknowledgement is required

Example:

```text
Release boundary: git_remote
Enabled adapters:
- local-record: local release_record, commit
- push-origin: git push origin main
Ship expectation:
- will_commit: true
- will_push: true
- will_run_script: false
```

### 第 4 步：指定 Feature 详情（可选）

如果用户指定了 feature 编号（如 `/bewater-status 001`），显示该 feature 的详细信息：
- feature.md 摘要
- tasks.md 进度（总任务数 / 已完成 / 待开始）
- 验证结果
- gate 状态

## 上下文预算规则

1. **优先读 Manifest**：先读 context-manifest.md 获取摘要，避免读取所有完整文档
2. **按需读详情**：仅在用户需要具体信息时才读取完整文档
3. **单 Feature 详情**：仅在用户指定编号或请求详情时读取

## 完成标准

- [ ] 已读取 state.json 和 context-manifest.md
- [ ] 已展示当前状态
- [ ] 已展示 gate 状态
- [ ] 已建议下一步操作
- [ ] 没有修改任何文件

## 输出合约

```json
{
  "status": "passed|failed|blocked",
  "artifacts": {
    "state_path": ".bewater/state.json",
    "manifest_path": ".bewater/context-manifest.md"
  },
  "blockers": [],
  "next_action": "{next_command from state.json}"
}
```
