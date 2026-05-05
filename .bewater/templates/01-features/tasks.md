# Tasks: {功能名称}

<!-- format-version: 1.0 -->
> **用途**: 由 bewater-plan skill 自动生成的任务拆解清单
> **生成命令**: `/bewater-plan`
> **输入**: feature.md（用户故事 + FR） + design.md（技术方案）

---

## 任务概览

**总任务数**: [N]
**预估工作量**: [X] 人天
**关键路径**: [关键路径描述]

---

## Tasks Gate Checklist（Plan 后硬门禁）

> 说明：`/bewater-plan` 完成 tasks.md 后必须执行本门禁。未通过不得进入 build。

### 1) 依赖完整性

- [ ] Setup / Foundational / Story / Polish 阶段依赖关系完整
- [ ] 每个有前置任务的条目都标注依赖（如 `依赖 T101, T102`）
- [ ] 不存在循环依赖
- [ ] 关键路径可追踪

### 2) 验收映射

- [ ] 每个用户故事至少有 1 个独立验证描述，并保留 `story_id`
- [ ] 每个 ready task 都有 `scenario_id` 或明确 AC reference
- [ ] 每组实现任务至少映射到 1 组测试任务
- [ ] 核心 FR/NFR 在任务中有对应落点
- [ ] `experience_surface=user_visible|mixed` 时，任务必须覆盖 discoverability affordance 与 minimal usage path，不能只覆盖隐藏后端能力

### 3) 风险覆盖

- [ ] 高风险任务已列入“高风险任务”表
- [ ] 每个高风险项有对应缓解措施
- [ ] 阻断风险已转换为可执行任务

### 4) 估算合理性

- [ ] 单任务估算在 2-8 小时范围内（超出需拆分或说明）
- [ ] 总估算与阶段规模一致，无明显失衡
- [ ] 并行任务标注 `[P]` 合理，不违反依赖

### Gate 结论（由 Plan 子代理填写）

- **tasks_gate_status**: `passed | failed`
- **blockers**:
  - [ ] [若失败，列出阻断项]
- **ready_for_build**: `true | false`

---

## Delivery Map

## Testing Asset Map

> E2E 自动化测试代码由 Build 阶段按 TDD 产出；Validate 阶段只运行、审计和补充对抗性检查。
> `static_verify` 可作为补充；`blackbox_smoke` 或 `formal_e2e` 才能覆盖用户可见边界；`agent-browser is supplemental`，只记录为 `exploratory_browser` 证据。

| scenario_id | test level | owner | test asset path | RED command | verify command | receipt |
|-------------|------------|-------|-----------------|-------------|----------------|---------|
| S-001 | static_verify + blackbox_smoke / formal_e2e | Builder | `tests/blackbox/example.sh` or `e2e/flows/example.spec.ts` | `curl -fsS http://127.0.0.1:5173/ | python3 scripts/assert-html.py --contains "Welcome"` | `npx playwright test e2e/flows/example.spec.ts --grep "@S-001"` | `receipts.json#T201` |

## Eval Asset Map

> Required only when `feature.md#ai_behavior_eval.required=true`.
> Build 阶段产出 AI eval asset；Validate only runs and audits AI eval assets.
> Missing required eval assets after Build are `implementation_gap`. Missing eval strategy or asset mapping before Build is `spec_package_drift`.

| scenario_id | eval level | dataset path | scorer or rubric | Eval RED command | verify command | result artifact | receipt |
|-------------|------------|--------------|------------------|------------------|----------------|-----------------|---------|
| S-001 | none / lite / standard / deep | `evals/{feature-id}/golden.jsonl` | `evals/{feature-id}/rubric.md` or deterministic scorer | `npm run eval:{feature-id}` | `npm run eval:{feature-id} -- --threshold 0.80` | `eval-results/{feature-id}.json` | `receipts.json#T201.eval_evidence` |

### Phase 1: Foundational

- [ ] T001 Prepare feature scaffolding
  - task_readiness: backlog
  - story_id: foundation
  - scenario_id: none
  - depends_on: none
  - parallel_group: none
  - Scenario / AC mapping: FR-001
  - test mapping: feature-specific regression
  - risk: medium

### Phase 2: Story 1 - Example Story (Priority: P1)

- [ ] T201 Implement first user-visible behavior
  - task_readiness: ready
  - story_id: US-001
  - scenario_id: S-001
  - depends_on: T001
  - parallel_group: none
  - Scenario / AC mapping: S-001 / AC-001 / FR-002
  - test mapping: unit + e2e asset
  - risk: high

#### Execution Block（task_readiness=ready 时必填）

**Story / scenario refs**
- story_id: US-001
- scenario_id: S-001
- acceptance_ref: AC-001

**Design refs**
- `design.md` §Per-Story Technical Approach

**Exact files in scope**
- Modify: `src/feature/example.py`
- Test: `tests/feature/test_example.py`
- E2E Test: `e2e/flows/example.spec.ts`

**Test level**
- static_verify
- blackbox_smoke
- formal_e2e
- exploratory_browser

**Callsites / reuse checklist**
- [ ] Reuse existing helpers before adding new ones
- [ ] Update all callsites touched by this feature

**RED command**
- `python3 -m pytest tests/feature/test_example.py::test_first_user_visible_behavior -q`

**Expected RED failure marker**
- `AssertionError`

**GREEN target**
- Minimal implementation that satisfies S-001 / AC-001 without broad refactors

**Verify commands**
- `python3 -m pytest tests/feature/test_example.py -q`
- `python3 -m pytest -q`
- `curl -fsS http://127.0.0.1:5173/ | python3 scripts/assert-html.py --contains "Welcome"`
- `npx playwright test e2e/flows/example.spec.ts --grep "@S-001"`

**E2E asset**
- driver: Playwright
- spec: `e2e/flows/example.spec.ts`
- scenario coverage: S-001 / AC-001

**E2E runtime**
- web server: `npm run dev -- --host 127.0.0.1`
- base URL: `http://127.0.0.1:5173`
- data/auth setup: `N/A — public guest flow`

**Evidence artifacts**
- Playwright trace: `test-results/**/trace.zip`
- Screenshot/video: `test-results/**`

**AI Behavior Eval asset**
- applicable: false
- required: false
- level: none
- dataset: `N/A — no AI behavior eval required`
- scorer or rubric: `N/A — no AI behavior eval required`
- Eval RED command: `N/A — no AI behavior eval required`
- verify command: `N/A — no AI behavior eval required`
- result artifact: `N/A — no AI behavior eval required`

**AI Behavior Eval receipt**
- If required, record optional `eval_evidence` inside `receipts.json#T{xxx}`.
- Required fields inside `eval_evidence`: `required`, `level`, `dataset`, `scorer`, `threshold`, `result_artifact`.

**Receipt path**
- `docs/01-features/{id-name}/receipts.json#T{xxx}`（每个 feature 一个 receipts.json，按 task ID 索引）

**Done definition**
- `task_readiness` is explicit for every task
- every ready task shows the full `Execution Block`
- quality strategy and TDD sections remain present

**Escalation notes**
- Escalate before changing shared APIs, persistence contracts, or the public state chain

---

## Constitution Compliance Notes

- checked_against: `docs/00-project/constitution.md`
- planning_result: pass|warn|blocked|not_applicable
- notes:
  - Visual quality principle considered for S-001 interaction polish.
  - T203 adds the required regression coverage before implementation is marked done.

---

## Pre-Build Readiness Review

> 说明：`/bewater-plan` 完成后必须执行，且结果直接决定 `tasks_gate` 是否可写为 `passed`。

- feature/design/tasks consistency: `pass | fail`
- overbuild risk: `pass | fail`
- underbuild risk: `pass | fail`
- test and validation mapping: `pass | fail`
- unresolved decisions: `none | list`
- ready task execution readiness: `pass | fail`

### Review Findings

- [ ] [记录发现 1]
- [ ] [记录发现 2]

### Review Decision

- `tasks_gate_status`: `passed | failed`
- `blockers`:
  - [ ] ...
- `ready_for_build`: `true | false`

---

## 质量策略（保留原有策略）

**按风险等级自动匹配**:
- Critical: TDD 必须 / 覆盖率 ≥ 80% / CR 必须
- High: TDD 必须 / 覆盖率 ≥ 70% / CR 必须
- Medium: TDD 必须 / 覆盖率 ≥ 60% / CR 抽检
- Low: TDD 必须 / 覆盖率 ≥ 50% / CR 可选

---

## TDD 执行记录

> **用途**: 记录每个任务的 TDD 执行过程，确保测试先行原则
> **更新时机**: 每完成一个任务的 RED-GREEN-REFACTOR 循环后更新

### Task 101 - TDD 执行记录

**TDD 阶段**:
- [ ] RED - 编写失败测试
- [ ] GREEN - 实现最小代码使测试通过
- [ ] REFACTOR - 重构优化（可选）

**测试文件**: `[测试文件路径]`
- 创建时间: YYYY-MM-DD HH:MM
- 测试用例数: [N]

**实现文件**: `[实现文件路径]`
- 创建时间: YYYY-MM-DD HH:MM
- 代码行数: [N]

**执行结果**:
- 测试通过率: [N/M]
- 覆盖率: [X]%

**备注**:
<!-- 记录 TDD 过程中的关键决策、遇到的问题、解决方案等 -->
