# SHARED_STATE_CONTRACT

> 仅供各 Skill 参考，不作为运行时强依赖。每个 Skill 必须自包含最小闭环。

## Public State Chain

`uninitialized → initialized → specified → planned → building → shipped`

## Command Mapping

- `uninitialized` → `/bewater-init`
- `initialized` → `/bewater-goal` | `/bewater-quick`
- `specified` → `/bewater-plan`
- `planned` → `/bewater-build`
- `building` → `/bewater-validate`
- `building` → `/bewater-ship`
- `building` + audit need → `/bewater-ship --precheck-only`
- `auto` from `building` + missing or stale `validation_outcome` → `/bewater-validate`

## Unified Status Enum

- 通用执行状态：`passed | failed | blocked`
- 发布决策状态：`go | no-go`
- build 内部调度字段：`completion_state = done | done_with_concerns | needs_context | blocked`（不扩展公开 gate）

## Feature Classification

- 功能分类字段：`complexity_tier`, `implementation_mode`
- `complexity_tier`：`lite | standard | deep`
- `implementation_mode`：`greenfield | extension | existing_partial | existing_complete`
- `extension` means this feature adds behavior to an existing app and must identify reused modules, modified callsites, and regression coverage.

## Gate Rules Snapshot

- `goal`：必须对话澄清；生成 `feature.md` 后必须完成 `feature_review_gate`；feature review passed 后才可自动触发 architect；强制检查 `design.md`
- `plan`：生成 `tasks.md` 并写入 `tasks_gate`；每个任务必须声明 `task_readiness`；ready task 需包含完整 `Execution Block`；必须完成 pre-build readiness review 后才可 `tasks_gate=passed`
- `build`：自动触发 review；review 顺序为 implementer -> spec review -> code quality review；结束后下一步是 `/bewater-validate`；existing implementation 模式下只负责补缺口
- E2E test assets are Build artifacts when planned; Validate runs and audits them. Missing planned E2E assets route to `implementation_gap`.
- `review`：只输出审查结论，写 `review_gate` 与 `review_note_path`
- `validate`：公开生命周期命令；由 QA 承担功能 + 安全 + 性能 + Spec consistency；写 `validation_report_path` 与 `validation_outcome`；不得写 `ship_precheck_gate`
- `planned` + `implementation_mode=existing_complete`：允许直接进入 `/bewater-validate`，validate-flow 必须先把状态推进到 `building`
- `auto`：从 `building` 自动推进时，若缺少 fresh `validation_outcome`，必须先路由到 `/bewater-validate`；默认 `go` 路径进入 `/bewater-ship` 完成 automatic local ship；`--precheck-only` 仅做审计；目标澄清与 remote release decision 属于 human gates，不属于 workflow confirmation
- `ship`：消费 validate 证据、合成 `ship_precheck_gate`，并在 Go 时执行 local release record + local commit；remote push/deploy/script 必须具备 explicit release intent 与 irreversible acknowledgement；证据缺失或过期时可自动触发 validate-flow 作为安全兜底；`--precheck-only` 只做审计检查；No-Go 禁止发布
- `quick`：仅限低风险变更；可跳过 `plan`；但必须保留最小 review + 最小 validate 证据

## Gate Ownership Matrix

| Gate | Writer | Readers | Notes |
|------|--------|---------|-------|
| `foundation_gate` | `/bewater-init` / init-flow | goal, status | project foundation readiness and first-slice handoff |
| `feature_review_gate` | `/bewater-goal` / goal-flow | architect, plan, status | source feature definition quality and US/S/AC/GWT traceability |
| `architect_gate` | `/bewater-goal` via architect-flow | plan, status | design quality and story coverage |
| `tasks_gate` | `/bewater-plan` | build, status | execution-ready task set |
| `prebuild_review_gate` | `/bewater-plan` | build, status | feature/design/tasks consistency |
| `review_gate` | `/bewater-build` / build-flow | ship, quick, status | implementation review result |
| `ship_precheck_gate` | `/bewater-ship` / ship-flow | ship, status | release authorization |

Ownership rule: validate-flow writes `validation_outcome`; ship-flow writes `ship_precheck_gate`.

## Flow and Capability Mapping

- `goal-flow` -> `product` -> `product-framing`
- `plan-flow` -> `planner` -> `planning-readiness` + `review-pack`
- `build-flow` -> `builder` + `reviewer` -> `tdd-implement` + `review-pack`
- `validate-flow` -> `qa` + `reviewer` -> `validation-pack` + `evidence-aggregate`
- `ship-flow` -> `qa` + `reviewer` -> `evidence-aggregate`

## Semantic Preflight Matrix

Skills must follow this matrix before writing lifecycle gates or advancing state:

For 4.0.0 convergence, plan preflight also checks intent review, split assessment, spec convergence, and coverage matrix completeness before `prebuild_review_gate=passed`.

| Boundary | Required preflight |
|----------|--------------------|
| goal/specify | `python3 .claude/scripts/bewater-check.py feature --feature <feature.md>` and `feature-review.md` with `feature_review_gate=passed` before architect |
| architect | `feature_review_gate=passed`, then `python3 .claude/scripts/bewater-check.py design --feature <feature.md> --design <design.md>` |
| plan | `bewater-check.py feature`, `bewater-check.py design`, `bewater-check.py plan`, and methodology backlog review |
| build | `python3 .claude/scripts/bewater-check.py plan --tasks <tasks.md>` before dispatch; `check-tdd-receipts.py` after completed implementation tasks |
| ship | `bewater-check.py plan`, `check-tdd-receipts.py`, state schema validation, and validation outcome schema validation |
| auto | run the next route's preflight and stop on any failure |
| doctor | `python3 .claude/scripts/bewater-check.py root --project-root .` in installed mode |

Default scope is the current feature. Shipped features are skipped unless an explicit include-shipped mode is requested by the caller.
