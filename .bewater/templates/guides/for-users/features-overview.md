# 功能概览

> 说明 BeWater 文档体系和命令体系分别负责什么。

## 文档分层

- `docs/00-project/`
  - 项目级约束（vision、architecture、constitution、decision-log）
- `docs/01-features/{编号}-{功能名}/`
  - 功能级执行文档（feature、tasks、review-note、validation-report）
- `docs/02-learning/`
  - 项目级知识沉淀（patterns、anti-patterns、retrospective）

## 命令职责

Public path: `goal -> plan -> build -> validate -> ship`
Public validation path: `goal -> plan -> build -> validate -> ship`

### 用户命令

- `/bewater-init`：项目初始化（一次性）
- `/bewater-goal`：创建功能目标和验收标准（自动触发架构评估）
- `/bewater-plan`：生成任务拆解与依赖关系
- `/bewater-build`：执行实现与测试（自动触发内审）
- `/bewater-validate`：生成验证证据、`validation-report.md` 与 `validation_outcome`
- `/bewater-ship`：消费验证证据、核验 release gate，并在 Go 时发布；证据缺失或过期时可自动补齐
- `/bewater-auto`：Feature 自动化入口：输入需求后推进 goal → plan → build → validate → ship precheck，遇阻断或 release boundary 即停
- `/bewater-next`：只读给出下一步建议
- `/bewater-status`：读取当前进度与状态
- `/bewater-learn`：学习回写
- `/bewater-quick`：低风险快捷路径（跳过 plan，仍要求最小验证）

## Quick Path Blocked Categories

`/bewater-quick` must not be used when the requested change involves:

- data migration
- security permission changes
- payment or billing behavior
- production release automation
- cross-module refactor
- irreversible operation

If any category matches, use the standard `goal -> plan -> build -> validate -> ship` path.

默认 `/bewater-auto` 只有两个必须停下来的人工闸口：goal 需求确认，以及 ship 前的 release decision。其余 `plan -> build -> validate -> ship precheck` 在无阻断时自动推进。

对于 user-visible features，BeWater validation 不只检查技术上存在，还必须验证 capability 可被发现，且普通用户能完成最小使用路径。

### What `/bewater-ship` Does

`/bewater-ship` ships the current validated feature/slice to the release boundary declared in `.bewater/release.json`.

- Default `local`: writes release record and local commit; no push or deploy.
- `git_push`: pushes to the configured Git remote after irreversible acknowledgement.
- `script`: runs the configured deploy/publish script after irreversible acknowledgement.

Run `/bewater-ship --precheck-only` to preview the release plan without commit, push, deploy, publish, or script execution.

### 内部命令

- `/bewater-architect`：由 goal 自动触发
- `/bewater-review`：由 build 或 quick 内部触发
- `validate-flow`：由 `/bewater-validate` 或 `/bewater-ship` 安全兜底触发

## 已有实现模式

已有实现（existing implementation）仍然使用相同命令集合，不新增新的 catchup 类公开命令：

- `implementation_mode=greenfield`：标准流程
- `implementation_mode=extension`：复用已有模块，记录 callsites 与回归覆盖，走 `/bewater-build -> /bewater-validate -> /bewater-ship`
- `implementation_mode=existing_partial`：`plan` 产出 gap analysis，`build` 补缺口
- `implementation_mode=existing_complete`：`plan` 可直接把下一步设为 `/bewater-validate`

## 标准状态链路

```text
uninitialized → initialized → specified → planned → building → shipped
```

> 注：`building` 内部只保留 implementing、reviewing、validating 三个执行提示，不再暴露额外公开状态。

## 什么时候算完成

- 功能级完成：`/bewater-ship` 已核验证据并进入 `shipped`
- 项目级完成：发布后完成 `/bewater-learn`，知识回写到 `docs/02-learning/`
