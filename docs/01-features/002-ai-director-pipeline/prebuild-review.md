---
feature_id: "002"
review_type: prebuild
reviewed_at: 2026-05-05
reviewed_by: /bewater-plan
status: passed
---

# Pre-Build Review: 002-AI 编导管线

## Spec Convergence

### feature.md ↔ design.md

| Aspect | feature.md | design.md | Converged |
|--------|-----------|-----------|-----------|
| LLM integration | FR-001: call real LLM | Skill adapter + OpenAI-compatible | YES |
| Script generation | FR-002: structured script output | script_generation.py with JSON schema | YES |
| Storyboard | FR-003/FR-004: StoryboardSegment | storyboard.py with full field set | YES |
| Review | FR-005/FR-006: structured findings | review_script.py with 5-field schema | YES |
| Task list | FR-010: task list page | GET /api/video-tasks + Web hash routing | YES |
| Artifact content | FR-012–FR-014: readable display | GET artifact content endpoint + Web rendering | YES |
| Error handling | FR-020/FR-021: error categories | 4 error categories in Skill design | YES |
| Skill adapter | FR-007: provider isolation | LLMAdapter class | YES |

### design.md ↔ tasks.md

| Design Component | Task Coverage | Converged |
|-----------------|---------------|-----------|
| LLM Adapter | T001 | YES |
| script_generation Skill | T002 | YES |
| storyboard Skill | T003 | YES |
| review_script Skill | T004 | YES |
| Task list API | T005 | YES |
| Artifact content API | T005 | YES |
| Web workbench upgrade | T005 | YES |
| E2E test strategy | T006, T007 | YES |
| AI eval strategy | T007 | YES |

---

## Coverage Matrix

| Scenario | Story | Design Ref | Task IDs | Test Mapping | Status | Gap |
|----------|-------|------------|----------|-------------|--------|-----|
| S-001 | US-001 | design.md "Skill 实现 > script_generation" | T001, T002, T005, T006, T007 | unit + integration + blackbox + eval | covered | none |
| S-002 | US-001 | design.md "Skill 实现 > storyboard" | T001, T003, T005, T006, T007 | unit + integration + blackbox + eval | covered | none |
| S-003 | US-001 | design.md "Skill 实现 > review_script" | T001, T004, T005, T006, T007 | unit + integration + blackbox + eval | covered | none |
| S-004 | US-002 | design.md "任务列表与导航" | T005, T006, T007 | unit + integration + blackbox | covered | none |

---

## Intent Review Check

- intent_review.required: true
- intent_review.status: confirmed
- intent_review.confirmed_by: user
- intent_review.confirmed_at: 2026-05-05 18:10 CST
- reviewed_items: user_story, non_goals, key_scenarios

**Result**: PASSED — intent review confirmed by user.

## Split Assessment Check

- user_value_points: 3
- scenarios_count: 4
- impacted_modules_count: 3
- unresolved_clarifications_count: 0
- complex_scenario_dependencies: false
- triggered_conditions: [] (0 conditions triggered)
- decision: proceed

**Result**: PASSED — no split conditions triggered.

## Experience Surface Check

- experience_surface: user_visible
- Entry points: `/workbench` (task list), `POST /api/video-tasks` (API)
- Discovery: Task list visible on landing, "创建新任务" button prominent
- Minimal usage path: `/workbench` → create → view script/storyboard/review
- Covered in design: YES (Section "Entry Points / Discovery Path")
- Covered in tasks: YES (T005 implements all UI and navigation)

**Result**: PASSED — discoverability and minimal usage path covered.

---

## Underbuild / Overbuild Check

### Underbuild Risk

- All 4 scenarios have task coverage: YES
- All scenarios have test mapping: YES
- AI eval required=true, eval strategy present: YES
- E2E test strategy covers all scenarios: YES
- Error handling has explicit task coverage: YES

**Result**: No underbuild detected.

### Overbuild Risk

- No editor capabilities (aligned with non-goals): CONFIRMED
- No TTS/subtitle/synthesis (aligned with non-goals): CONFIRMED
- No material download (aligned with non-goals): CONFIRMED
- LLM adapter only does chat completion (P3 compliance): CONFIRMED
- Web uses vanilla HTML/JS (no framework): CONFIRMED

**Result**: No overbuild detected.

---

## Fake-Ready Task Check

| Task | readiness | Execution Block | Test Mapping | AC/Scenario Refs | Verdict |
|------|-----------|----------------|-------------|-------------------|---------|
| T001 | ready | Complete | 6 tests | S-001,S-002,S-003 | genuine ready |
| T002 | ready | Complete | 5 tests | S-001/AC-001 | genuine ready |
| T003 | ready | Complete | 5 tests | S-002/AC-002 | genuine ready |
| T004 | ready | Complete | 5 tests | S-003/AC-003 | genuine ready |
| T005 | backlog | Skeleton provided | 5 tests planned | S-001~S-004/AC-001~AC-004 | correct backlog |
| T006 | backlog | Skeleton provided | 5 tests planned | S-001~S-004 | correct backlog |
| T007 | backlog | Skeleton provided | 2 test assets planned | All | correct backlog |

**Result**: No fake-ready tasks.

---

## Concerns

1. T002–T004 并行执行时需注意 step_runner.py 的合并冲突（建议串行提交或协调修改区域）。
2. Web 工作台（T005）范围较大，需严格控制为可读展示，不做编辑。

## Blockers

None.

## Verdict

**passed** — Feature/design/tasks 三者收敛，4 个 ready task 可直接进入 build，3 个 backlog task 依赖合理。
