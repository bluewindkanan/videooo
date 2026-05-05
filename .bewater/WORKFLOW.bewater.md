# BeWater 工作流详解

> **版本**: 4.0.0 | **日期**: 2026-04-30
> **定位**: 流程逻辑 SSOT（Single Source of Truth）- 阶段顺序、命令边界、状态转换规则

Version: 4.0.0
Published: 2026-04-30

Public path: `init -> goal -> plan -> build -> validate -> ship`
Public validation path: `goal -> plan -> build -> validate -> ship`

Public skills:
- `/bewater-init`
- `/bewater-goal`
- `/bewater-plan`
- `/bewater-build`
- `/bewater-validate`
- `/bewater-ship`
- `/bewater-auto`
- `/bewater-next`
- `/bewater-status`

Internal flow ownership:
- `validate-flow` owns validation evidence synthesis
- `ship-flow` owns release precheck and release execution routing

BeWater exposes 6 public lifecycle commands: init, goal, plan, build, validate, and ship. It also exposes 6 public utility commands, 3 internal flow skills, and 6 capability-pack skills.

默认 `/bewater-auto` 只有两个必须停下来的人工闸口：goal 需求确认，以及 ship 前的 release decision。其余 `plan -> build -> validate -> ship precheck` 在无阻断时自动推进。

### Release Boundary

BeWater ships to the configured release boundary in `.bewater/release.json`.
Default is local release record plus commit. Enabling `git_push` means `/bewater-ship` pushes to the configured Git remote after acknowledgement. Enabling `script` means `/bewater-ship` runs the configured deploy or publish script after acknowledgement.

For user-visible features, BeWater validation does not stop at technical existence. It must also verify that the capability can be discovered and that a normal user can complete the minimal intended usage path.

### What `/bewater-ship` Does

`/bewater-ship` ships the current validated feature/slice to the release boundary declared in `.bewater/release.json`.

- Default `local`: writes release record and local commit; no push or deploy.
- `git_push`: pushes to the configured Git remote after irreversible acknowledgement.
- `script`: runs the configured deploy/publish script after irreversible acknowledgement.

Run `/bewater-ship --precheck-only` to preview the release plan without commit, push, deploy, publish, or script execution.

Current runtime inventory:

- 20 skills total
- 14 BeWater lifecycle/utility/internal skills
- 6 capability-pack skills: `product-framing`, `planning-readiness`, `review-pack`, `tdd-implement`, `validation-pack`, `evidence-aggregate`
- 8 agents: `SHARED_AGENT_BASE.md`, `architect.md`, `builder.md`, `inspector.md`, `planner.md`, `product.md`, `qa.md`, `reviewer.md`

## Current References

- `docs/reference/command-surface.md`
- `docs/reference/runtime-contracts.md`
- `docs/reference/skill-agent-inventory.md`
- `docs/reference/capability-packs.md`
- `docs/reference/semantic-gates.md`
- `docs/reference/release-intent-policy.md`
- `.bewater/contracts/template-tier.schema.json`

---

## 概述

BeWater 是一套可安装、可复用的软件开发 harness。它把完整开发流程拆成：

- 9 个内部执行阶段
- 6 个公开状态
- 6 个生命周期命令 + 6 个公共工具命令 + 3 个内部 flow skills + 6 个 capability-pack skills
- 1 条严格的验证闭环

用户标准流程：

```text
init → goal → plan → build → validate → ship
```

面向功能开发的最短完整路径：

```text
goal → plan → build → validate → ship
```

公开状态链保持不变：

```text
uninitialized → initialized → specified → planned → building → shipped
```

---

## 9 阶段执行逻辑

```text
Init → Goal → Architecture → Plan → Build → Review → Validate → Ship → Learn
```

| 阶段 | 负责组件 | 主要产物 | 说明 |
|------|----------|---------|------|
| Init | `/bewater-init` | `vision.md` `product-plan.md` `architecture.md` `constitution.md` `decision-log.md` `foundation-review.md` | 建立项目级北极星与约束，并推荐首个功能候选 |
| Goal | `/bewater-goal` | `feature.md` | 明确问题、边界、成功标准 |
| Architecture | `/bewater-architect` | `design.md` `research.md` | 由 goal 自动触发，按复杂度展开 |
| Plan | `/bewater-plan` | `tasks.md` | 任务拆解、依赖、风险、测试映射、Pre-Build Readiness Review |
| Build | `/bewater-build` | 代码 + 测试 | 只负责实现与 Builder 回执 |
| Review | `/bewater-review` | `review-note.md` | 内部审查，写 `review_gate` |
| Validate | `/bewater-validate` | `validation-report.md` | 生成可审计验证证据与 `validation_outcome` |
| Ship | `/bewater-ship` | 发布记录 | precheck 内部补齐/核验证据后执行发布 |
| Learn | `/bewater-learn` | `patterns.md` `anti-patterns.md` `retrospective.md` | 发布后沉淀经验 |

---

### Vision vs Product Plan vs Feature Framing

BeWater intentionally does not create PRD artifacts.

The product framing chain is:

```text
vision.md -> product-plan.md -> feature.md -> design.md -> tasks.md
```

- `/bewater-init` uses Vision Discovery: open-ended co-discovery with the creator, then writes `vision.md` as a north-star decision filter.
- `/bewater-init` also writes `product-plan.md`: an MVP-first feature-candidate map that explains what should be done next and why.
- `product-plan.md` may contain candidate sequencing, MVP learning-loop rationale, Now / Next / Later alignment, and recommended next candidate, but not date-based roadmap commitments.
- `/bewater-goal` uses Feature Option Framing: convergent requirement clarification, 2-3 proposed approaches, explicit selected approach, then writes `feature.md` as the source requirement contract.
- `feature.md` must link back to `vision.md`; when started from product-plan, it should also record the source candidate ID.
- `product-plan.md` is not executable. Automation must route through `/bewater-goal`, `/bewater-plan`, and the normal gates.

## 命令边界

### 用户可调用命令

| 命令 | 职责 | 自动触发 |
|------|------|---------|
| `/bewater-init` | 初始化项目级文档和目录，完成 foundation review，推荐首个功能候选 | - |
| `/bewater-goal` | 目标框定 | `/bewater-architect` |
| `/bewater-plan` | 任务拆解、`Execution Block` 补全与 readiness review | - |
| `/bewater-build` | TDD 实现与 Builder 调度 | `/bewater-review` |
| `/bewater-validate` | 执行 QA 验证，生成 `validation-report.md` 与 `validation_outcome` | validate-flow |
| `/bewater-ship` | 执行 precheck、必要时自动补齐验证证据，并在 release 模式发布 | validate-flow fallback |
| `/bewater-auto` | Feature 自动化入口：输入需求后推进 goal → plan → build → validate → ship precheck，遇阻断或 release boundary 即停 | 内部按状态机选择命令 |
| `/bewater-next` | 只读推荐下一步 | 不改状态 |
| `/bewater-status` | 查看状态、gate freshness、证据与阻断 | 不改状态 |
| `/bewater-learn` | 发布后学习回写 | - |
| `/bewater-eval` | 方法论和交付效果评估 | 不改 delivery state |
| `/bewater-quick` | 低风险快捷路径，跳过 plan，仍要求最小验证 | 轻量 review + 最小 validate |

### 关键边界

- `/bewater-build` 只负责实现与 review，不负责发布判断
- `/bewater-validate` 公开生成证据与 `validation_outcome`，validate-flow must not write `ship_precheck_gate`
- `/bewater-ship` 负责消费并核验 validate 证据、合成 `ship_precheck_gate`，并在 Go 时发布；当证据缺失或过期时可自动触发 validate-flow 作为安全兜底
- `/bewater-ship --precheck-only` 只执行审计/CI 检查，不进入 `shipped`
- `/bewater-quick` 可以跳过 plan，但不能跳过证据
- `/bewater-plan` 只有在任务清单与 `Pre-Build Readiness Review` 都完成后才算完成
- `tasks_gate=passed` 表示下一组 dispatchable ready tasks 已可执行，不只是“列出了任务”
- `/bewater-plan` must not mark `prebuild_review_gate=passed` until `feature.md`, `design.md`, `tasks.md`, and `prebuild-review.md` converge. Convergence means every feature scenario has design coverage, task coverage, and test mapping; required intent review is confirmed or overridden; and split assessment is proceed or explicitly overridden.

### Runtime Semantic Hardening

- `bewater-check.py` 是 runtime semantic checker，负责在 lifecycle 边界检查 `feature`、`design`、`plan` 与 installed `root`。
- `feature.md` 的 frontmatter scenarios 是 acceptance contract；后续 `design.md` scenario coverage 和 `tasks.md` 执行计划必须保留对应 scenario IDs。
- `implementation_mode=extension` 表示在已有应用上扩展能力，必须记录复用模块、修改 callsites 与回归覆盖面。
- 完成的 implementation task 使用 feature 级 `receipts.json` 保存 TDD receipt，`tasks.md` 通过 `receipts.json#Txxx` 引用。
- Feature docs are historical delivery claims, not automatic current-system truth. Agents should read `docs/00-project/project-context.md` before deep feature docs, and only treat feature docs as current when `last_verified_commit` plus `implementation_paths` remain fresh against code.
- `bewater-check.py feature --project-root <root>` reports `docs_may_be_stale` when implementation files changed after `last_verified_commit`.
- `.claude/skills/SHARED_STATE_CONTRACT.md` 的 `Semantic Preflight Matrix` 是各 skill 的共享预检路由；`/bewater-auto` 遇到语义失败必须停止。
- `bewater-ci-gate-check.py` 与 `bewater-ci-ship.py` 会重新运行语义预检；若 artifact 与 checker 不一致，返回 `semantic_preflight_failed`，不能只信 `.bewater/state.json` 中的 gate 状态。
- Pending gate 允许 `produced_by: null`，非 pending gate 必须有非空 producer；installed mode 下 `bewater-check.py root` 校验 `application_root`。
- 已 shipped feature 默认不因新 checker 失败而阻断迁移，除非调用者显式选择 include-shipped。

---

## 状态机

公开状态链：

```text
uninitialized → initialized → specified → planned → building → shipped
```

### 状态含义

| 状态 | 含义 |
|------|------|
| `uninitialized` | 缺少项目级基础文档 |
| `initialized` | 项目级基础文档已建立 |
| `specified` | 功能目标、设计与边界已明确 |
| `planned` | `tasks.md` 已通过 `tasks_gate`，且当前存在 execution-ready tasks |
| `building` | 正在实现或补证据 |
| `shipped` | 发布完成，且证据已核验 |

### `building` 的内部子阶段

```text
implementing → reviewing → validating
```

这三个子阶段只作为执行提示存在，不再对外暴露额外公开状态。

---

## 标准状态转换

| 当前状态 | 触发命令 | 下一状态 | 说明 |
|---------|---------|---------|------|
| `uninitialized` | `/bewater-init` | `initialized` | 初始化完成，并要求用户确认首个功能候选后进入 `/bewater-goal` |
| `initialized` | `/bewater-goal` | `specified` | 目标已框定，含自动 architect |
| `specified` | `/bewater-plan` | `planned` 或保持 `specified` | 由 `tasks_gate` 决定；需完成 readiness review |
| `planned` | `/bewater-build` | `building` | 进入实现期 |
| `planned` | `/bewater-validate`（已有实现例外） | 保持 `building` | 先提升到 `building`，再生成验证证据 |
| `building` | `/bewater-validate` | 保持 `building` | 生成/刷新 `validation-report.md` 与 `validation_outcome` |
| `building` | `/bewater-ship --precheck-only` | 保持 `building` | 核验证据并合成 precheck gate，不发布 |
| `building` | `/bewater-ship` | `shipped` 或保持 `building` | 只有证据核验通过才可发布 |
| `shipped` | `/bewater-learn` | 保持 `shipped` | 沉淀学习结果 |

---

## `build -> validate -> ship` 主链路

### Build

- 输入：`feature.md` `design.md` `tasks.md`
- 输出：代码、测试、Builder 回执、`review_gate`
- 结果：状态保持在 `building`
- 下一步：`/bewater-validate`

### Validate

- 输入：实现结果 + 规格文档
- 输出：`validation-report.md`
- Gate ownership: validate-flow 写 `validation_outcome`；ship-flow 写 `ship_precheck_gate`
- 结果：状态保持在 `building`
- 下一步：`/bewater-ship` 或返回 `/bewater-build`

### AI Behavior Eval Track

AI behavior features still use the same public lifecycle. The difference is that eval evidence must be defined and produced before final validation:

```text
Goal: classify ai_behavior_eval
Architect: define AI Behavior Evaluation Strategy
Plan: create Eval Asset Map
Build: produce eval assets and Eval RED/GREEN receipt evidence
Validate: run and audit planned eval assets
Ship: consume validation_outcome only
```

This introduces no new public command. `/bewater-eval` remains an optional utility outside delivery state for rerunning or reviewing planned AI behavior eval suites.

已有实现（existing implementation）例外：

- `implementation_mode=extension` 时，复用已有模块，记录 callsites 与回归覆盖，走 `/bewater-build -> /bewater-validate -> /bewater-ship`
- `implementation_mode=existing_complete` 时，`/bewater-plan` 可直接把下一步指向 `/bewater-validate`
- precheck 从 `planned` 进入时，必须先把状态提升到 `building`
- 只有发现真实实现缺口时，才回到 `/bewater-build`

### Ship

- 默认 `/bewater-ship` 必须消费/核验 validate 证据；证据缺失或过期时可自动触发 validate-flow 补齐证据
- `--precheck-only` 必须核验 validate 证据，但不得发布
- 不能直接把状态写成 `shipped`
- 只有在以下条件同时满足时才允许发布：
  - `review_gate.status = passed`
  - `ship_precheck_gate.status = go`
  - `artifacts.validation_report_path` 已记录且文件存在
  - `gates.ship_precheck_gate.evidence_checked = true`

---

## Quick Path

Quick 是低风险快捷路径，不是“无验证路径”。

适用变更：

- CSS/样式调整
- 文案修改
- 小范围重构
- 配置微调
- 单文件低风险 bug 修复

Quick 规则：

- 可以跳过 `plan`
- 必须保留最小验证
- 必须写入轻量 `review-note.md`
- 必须写入轻量 `validation-report.md`
- 只有最小验证证据齐全时才允许进入 `shipped`

---


## 失败与回退

| 场景 | 处理方式 |
|------|---------|
| `tasks_gate` 失败 | 保持 `specified`，修正规划后重跑 `/bewater-plan` |
| review 失败 | 保持 `building`，修复后重跑 `/bewater-build` |
| precheck 失败 | 保持 `building`，补证据或修复实现后重跑 `/bewater-ship` |
| ship 证据核验失败 | 保持 `building`，禁止进入 `shipped` |
| 发布执行失败 | 保持 `building`，修复发布问题后重跑 `/bewater-ship` |

---

## Install Surface Contract

- 方法论 `README.md` 属于安装面的一部分，不是可选文件
- 若目标项目没有根 `README.md`，安装到根目录 `README.md`
- 若目标项目已有根 `README.md`，安装 fallback：`.bewater/README.bewater.md`
- `.bewater/install-meta.json` 必须记录 `workflow_doc` 与 `readme_doc`
- `bewater-doctor.sh` 必须按 metadata 校验声明路径存在

---

## 相关文档

- `README.md` - 方法论定位与安装说明
- `CLAUDE.md` - 核心配置 SSOT
- `templates/core/state-machine.md` - 状态机完整定义
- `templates/core/state.md` - 状态持久化字段契约说明
- `templates/core/state-template.json` - 可解析状态模板
- `templates/core/command-boundaries.md` - 命令职责边界

---

**版本**: 4.0.0 | **最后更新**: 2026-04-30
