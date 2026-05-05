# Pre-Build Readiness Review: 001-knowledge-task-skeleton

feature: 001-knowledge-task-skeleton
review_type: prebuild_readiness
created_at: 2026-05-05
created_by: /bewater-plan
gate_name: prebuild_review_gate
recommended_gate_status: passed
recommended_next_action: "/bewater-build"
input_refs:
  - docs/01-features/001-knowledge-task-skeleton/feature.md
  - docs/01-features/001-knowledge-task-skeleton/design.md
  - docs/01-features/001-knowledge-task-skeleton/tasks.md
evidence_refs: []

## Spec Convergence

### Scenario coverage convergence

| scenario_id | In feature.md | Covered in design.md | Covered in tasks.md | Notes |
|---|---:|---:|---:|---|
| S-001 | yes | yes | yes | tasks 已规划 API/Worker/Web + smoke + eval |
| S-002 | yes | yes | yes | tasks 已规划 retry policy + retention + smoke |

### Design-to-task traceability (high level)

| design area | Task(s) |
|---|---|
| API endpoints（create/status/artifacts/retry） | T004 |
| Data model（VideoTask/WorkflowStep/TaskArtifact） | T002 |
| Artifact-First + failure retention | T003 |
| StepRunner + RetryPolicy + mutual exclusion | T005 |
| Web discovery + minimal usage path | T006 |
| Blackbox smoke scripts | T007 |
| AI Behavior Evaluation Strategy (lite) | T008 |

### Drift check
- 发现的潜在 drift：design.md 给出了 `python -m app.evals.run_001` 的命令假设；repo 当前 `app/` 仅有 README。tasks.md 已把 **Python package layout bootstrap** 作为 T001，避免 build 阶段临时改 design。
- 允许的降级：素材 link 下载/解析不稳定已在设计中声明为“需要用户动作 + 上传素材降级提示”，tasks 已覆盖为失败分类与 UI 提示（不强制首版完成上传实现）。

结论：**spec 内容一致**，但存在 **execution readiness 不足**（见 tasks_gate 部分）。
结论更新：已补齐可分发的 ready 批次（T001/T002/T003/T004/T007），可进入 build。

---

## Coverage Matrix

| Scenario | Story | Design Ref | Task IDs | Test Mapping | Status | Gap |
|---|---|---|---|---|---|---|
| S-001 | US-001 | design.md: Story Mapping / API / E2E / Eval | T002,T003,T004,T005,T006,T007,T008 | blackbox_smoke + lite eval | planned | T004/T007/T008 需要进入 ready 批次以保证可执行证据链 |
| S-002 | US-001 | design.md: RetryPolicy / E2E / Eval | T002,T003,T004,T005,T006,T007,T008 | blackbox_smoke + retry unit/integration + lite eval | planned | 同上；另外需要明确互斥/幂等实现策略 |

### Cross-cutting coverage view (quick scan)

| Scenario | UX path | API boundary | Worker/step | Artifacts | Retry | Blackbox smoke | AI eval |
|---|---|---|---|---|---|---|---|
| S-001 | T006 | T004 | T005 | T003 | N/A | T007 | T008 |
| S-002 | T006 | T004 | T005 | T003 | T005 | T007 | T008 |

---

## 3) Intent Review & Split Assessment（来自 feature.md 的硬约束）

### Intent review
- required: true
- status: confirmed（feature.md 已确认）
- outcome: pass

### Split assessment
- decision: proceed（feature.md）
- outcome: pass

---

## 4) Tasks Gate（可执行性：ready tasks + execution blocks + test mapping）

### What counts as “ready”
ready task 必须包含：scenario/AC 映射、测试映射、依赖、风险、以及完整 Execution Block（files in scope + RED/GREEN + verify + receipt）。

### Current assessment
- ready tasks:
  - T001（应用骨架 + 测试框架）
  - T002（核心数据模型 + SQLite 持久化最小实现）
  - T003（ArtifactStore：失败留痕 + 历史保留）
  - T004（4 个 API 端点 + 集成测试）
  - T007（blackbox smoke 脚本）
- receipts.json:
  - 已创建 `docs/01-features/001-knowledge-task-skeleton/receipts.json`（build 阶段逐步填写）

结论：recommended `tasks_gate` = **passed**（存在可直接进入 build 的可分发 ready 批次，且每个 ready 任务均包含 Execution Block）。

---

## 5) Prebuild Review Gate（收敛审查结论）

### Key risks (must watch)
- 状态机/幂等与 artifact retention 若实现不严谨，会导致 retry 场景证据无法闭环。
- 如果 smoke 脚本对运行环境（端口、启动方式、DB 路径、artifact_dir）不明确，validate 会不可复现。
- AI eval 若变成主观评价，无法审计；必须保持 deterministic rubric + schema_check。

### Recommendation
- recommended_gate_status: **passed**
- proceed checklist（build 阶段必须优先确认）：
  1) 先完成 T001→T004 的最小闭环，再跑 T007 blackbox smoke，确保证据链可复现。
  2) 在实现 retry 幂等/互斥时，优先保证“同 step 不并发执行、失败可重试且不覆盖历史产物”。
  3) build 阶段按 receipts.json 逐项记录 RED/GREEN/verify 命令与文件清单，避免证据漂移。
