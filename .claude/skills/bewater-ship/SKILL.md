---
name: bewater-ship
description: 消费并核验 validate 证据，在 Go 且具备发布意图时顺序执行发布
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
user-invocable: true
context: validation-report.md + ship gates + release evidence
effort: medium
---

# BeWater Ship

发布前必须消费并核验 validate 证据；当证据 missing or stale（缺失或过期）时，`/bewater-ship` may auto-trigger validate-flow 完成校验，再由 ship-flow 汇总 gate。默认用户体验是在 gate=go 时执行 local release adapter（release record + local commit），然后提示用户是否 push 到 GitHub、部署/运行脚本、执行 `/bewater-learn` 或停止。禁止跳过证据核验直接把状态写成 `shipped`。

推荐前置命令：`/bewater-validate`
安全兜底：当 validate 证据缺失或过期时，`/bewater-ship` may auto-trigger validate-flow before synthesizing `ship_precheck_gate`.
当前命令：`/bewater-ship`

## Execution Modes
- default: `precheck-and-release`
- audit only: `--precheck-only`

## Flow
bewater-ship
  -> ship-flow
  -> validate-flow (if evidence missing or stale)
  -> ship-flow synthesizes `ship_precheck_gate` from `validation_outcome`, freshness checks, and release-policy checks
  -> release execution when gate=go and release intent is present

Gate ownership: only `ship-flow` writes `ship_precheck_gate`. validate-flow writes `validation_outcome` and `validation-report.md`; ship-flow consumes them, checks freshness and release policy, then writes `gates.ship_precheck_gate.status` and `gates.ship_precheck_gate.evidence_checked`.

## Failure Routing
- `implementation_gap` -> `/bewater-build`
- `spec_package_drift` -> `/bewater-plan`
- `goal_scope_contradiction` -> `/bewater-goal`
- `release_execution_failure` -> stay in `building.ready_to_ship`

## Release Authorization
- Local release record and local commit do not require irreversible acknowledgement when `ship_precheck_gate.status=go`, evidence is fresh, and the release plan contains no unrelated dirty worktree changes.
- Remote effect adapters (`git_push` and `script`) must not release or execute unless `runtime.release_intent.intent=release` and `runtime.release_intent.irreversible_acknowledged=true`.
- If intent is missing or `audit-only`, `/bewater-ship` may still complete local release actions, but must skip remote effects and report the blocker for push/deploy/script execution.
- `runtime.release_intent` may come from the user invoking `/bewater-ship`, trusted wrappers, or interactive confirmation after current precheck results are shown.
- after local ship completes, present the release plan and ask the user whether to stop, push to GitHub, deploy/run configured scripts, run `/bewater-learn`, or start the next feature.
- `--precheck-only` explicitly clears all release execution for audit/CI usage.
- clear `runtime.release_intent` after successful remote release, lifecycle regression, or reviewed-input drift.
- `release_execution_failure` must not invalidate gate freshness by itself.

## PM-Facing Output: Release Decision

Default user-facing output should make the release choice explicit before showing adapter details.

The Release Decision must answer:

- Is this safe to release?
- What release boundary will execute?
- Is irreversible acknowledgement required?
- What evidence supports go/no-go?

Link the summary to `validation-report.md`, `release-record.md` when present, and `.bewater/release.json`. Internal gate names are secondary; use them only after the plain-language summary.

## Release Adapter Contract

`/bewater-ship` reads `.bewater/release.json`. If the file is missing, use local default:

```json
{
  "version": 1,
  "release_boundary": "local",
  "adapters": [
    {"id": "local-record", "type": "local", "enabled": true, "actions": ["release_record", "commit"]}
  ]
}
```

Supported release adapter types:
- `local`: writes release record and optional commit/tag; never pushes or deploys.
- `git_push`: pushes branch and optional tags to a Git remote; requires irreversible acknowledgement.
- `script`: runs a configured project script for deploy/publish; requires irreversible acknowledgement.

Before executing adapters, print a release plan with `release_boundary`, enabled adapters, `will_commit`, `will_push`, `will_run_script`, and `requires_irreversible_ack`.

`--precheck-only` must not execute commit, tag, push, or script adapters.

## Adapter Execution Order

1. Validate evidence freshness.
2. Synthesize `ship_precheck_gate`.
3. If `--precheck-only`, stop after reporting gate and evidence paths.
4. Build the release plan from `.bewater/release.json` or the local default.
5. Execute local adapter actions (`release_record`, `commit`, optional local `tag`) when gate=go and the worktree contains only intended changes.
6. If remote effects exist, require `runtime.release_intent.intent=release` and `runtime.release_intent.irreversible_acknowledged=true` before executing `git_push` or `script` adapters.
7. Record each adapter result in `release-record.md`.
8. Move to `shipped` when required local actions pass and no required remote action failed.

## Trigger

- build 与 validate 完成后准备发布时使用。

## State

- 前置：`building`
- 后置：`shipped` 或 `building`
- 下一步：`/bewater-learn` 或 `/bewater-build`

## Gate（强制）

1. 必须具备 validate 证据（缺失/过期时由 `/bewater-ship` 内部补齐）
2. `review_gate.status = passed`
3. `ship_precheck_gate.status = go`
4. 必须存在 `artifacts.validation_report_path`
5. `validation-report.md` 必须包含：
   - `release_decision: go`
   - `## E2E 测试结果`
   - `## Spec Consistency`

## 执行步骤

1. 读取 `.bewater/state.json`，确认 `current_state = building`
2. 校验 `review_gate.status = passed`
3. 检查 `artifacts.validation_report_path` 是否存在且新鲜；若缺失/过期，进入 validate-flow 生成新证据
4. 由 ship-flow 基于 `validation_outcome`、freshness 与 release policy 汇总 `ship_precheck_gate`
   - 写入 `gates.ship_precheck_gate.status = go|no-go`
   - 写入 `gates.ship_precheck_gate.evidence_checked = true`
5. `ship_precheck_gate != go` 时，保持 `building`
6. `--precheck-only` 时保持 `building`，输出 gate 与证据路径，不执行 local commit、tag、push、deploy 或 script
7. 默认模式下在 gate=go 时执行 local release adapter（release record + local commit）；remote push/deploy/script 仅在具备 explicit release intent 和 irreversible acknowledgement 时执行
8. 发布成功后更新 `.bewater/state.json`：
   - `current_state = shipped`
   - `gates.ship_precheck_gate.evidence_checked = true`
   - 保留 `artifacts.validation_report_path`

## 禁止事项

- 禁止跳过 validate 证据
- 禁止在无证据或 no-go 条件下发布
- 禁止用口头说明替代 artifact 核验
- 禁止证据不完整时标记 `shipped`
- 禁止把 `--precheck-only` 结果写成 `shipped`

## 状态变更指令（强制）

```json
{
  "current_state": "shipped",
  "shipped_at": "[ISO日期]",
  "gates": {
    "ship_precheck_gate": {
      "status": "go",
      "blockers": [],
      "updated_at": "[ISO时间]",
      "evidence_checked": true
    }
  },
  "artifacts": {
    "validation_report_path": "docs/01-features/[编号]-[名称]/validation-report.md"
  },
  "next_command": "/bewater-learn 或 /bewater-goal"
}
```

## 输出合约

```json
{
  "status": "shipped|blocked",
  "release_boundary": "local|git_remote|script",
  "release_plan": {
    "will_commit": true,
    "will_push": false,
    "will_run_script": false
  },
  "adapters": [{"id": "local-record", "status": "passed"}],
  "artifacts": {"validation_report_path": "...", "release_record": "..."},
  "gate": {"name": "ship_precheck_gate", "status": "go|no-go", "evidence_checked": true},
  "blockers": [],
  "next_action": "/bewater-learn | push-to-github | deploy | /bewater-build",
  "release_decision": "go|no-go"
}
```

Semantic preflights are defined in `.claude/skills/SHARED_STATE_CONTRACT.md` under "Semantic Preflight Matrix"; run the relevant check before writing a passed gate or advancing state.
