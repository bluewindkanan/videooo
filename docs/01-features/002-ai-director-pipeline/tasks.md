# Tasks: AI 编导管线（Feature 002）

> feature_id: 002
> complexity_tier: standard
> implementation_mode: extension
> generated_at: 2026-05-05

## Constitution Compliance Notes

| Principle | Compliance | Task Coverage |
|-----------|-----------|---------------|
| P1: Evidence-First Delivery | Every implementation task has corresponding tests and TDD receipts | All tasks |
| P2: User-Visible Slice First | This feature directly delivers user-visible AI director output and usable Web workbench | T001–T007 |
| P3: Simplicity Over Speculation | LLM adapter only does chat completion; no embedding/RAG/agent framework | T001 |
| P4: Use Existing Architecture | Reuses FastAPI/SQLite/Artifact architecture from Feature 001 | All tasks |
| P5: Boundary Validation | API integration tests + blackbox smoke for every user-visible scenario | T006, T007 |
| P6: Workflow Over Editor | Web only does readable display, no editing | T005 |
| P7: Reviewable Automation | Each Skill preserves llm_raw + parsed_json dual artifacts | T002–T004 |
| P8: Rights-Aware Inputs | Web retains source links disclaimer | T005 |
| P9: Artifact-First | Every step writes traceable artifacts | T002–T004 |

---

## Task Overview

| ID | Status | Depends On | Type | Receipt |
|----|--------|------------|------|---------|
| T001 | done | — | implementation | receipts.json#T001 |
| T002 | done | T001 | implementation | receipts.json#T002 |
| T003 | done | T001 | implementation | receipts.json#T003 |
| T004 | done | T001 | implementation | receipts.json#T004 |
| T005 | done | T002, T003, T004 | implementation | receipts.json#T005 |
| T006 | done | T002, T003, T004, T005 | implementation | receipts.json#T006 |
| T007 | done | T006 | implementation | receipts.json#T007 |

### Parallel Groups

- **PG-1**: T002, T003, T004（三个 Skill 互相独立，可并行）

---

### T001: LLM Adapter 基础设施

- **Story/Scenario refs**: US-001 (S-001, S-002, S-003)
- **AC refs**: AC-001, AC-002, AC-003
- **FR refs**: FR-001, FR-007, FR-020, FR-021
- **Design refs**: design.md "LLM Skill Adapter"
- **task_readiness**: `done`

#### Scope

- **Exact files in scope**:
  - NEW: `app/src/skills/__init__.py`
  - NEW: `app/src/skills/llm_adapter.py`
  - NEW: `app/tests/unit/test_llm_adapter.py`

#### Callsites / Reuse Checklist

- `app/src/workers/step_runner.py` — will import from skills (modified in T002–T004)
- No existing code imports skills yet (new module)

#### Test Mapping

| Level | Test | Coverage |
|-------|------|----------|
| unit | `test_llm_adapter.py::test_chat_success` | Mock HTTP, verify request format and response text |
| unit | `test_llm_adapter.py::test_chat_rate_limit` | Mock 429, verify error category |
| unit | `test_llm_adapter.py::test_chat_api_error` | Mock 5xx, verify error category |
| unit | `test_llm_adapter.py::test_chat_parse_error` | Mock malformed response, verify error handling |
| unit | `test_llm_adapter.py::test_chat_content_filter` | Mock content safety block, verify non_retryable |
| unit | `test_llm_adapter.py::test_env_config` | Verify env var loading |

#### Execution Block

```
Story / scenario refs: US-001 (S-001, S-002, S-003)
Design refs: design.md "LLM Skill Adapter"

Exact files in scope:
  - app/src/skills/__init__.py (NEW)
  - app/src/skills/llm_adapter.py (NEW)
  - app/tests/unit/test_llm_adapter.py (NEW)

Callsites / reuse checklist:
  - step_runner.py will import skills (not modified in this task)

RED command:
  pytest app/tests/unit/test_llm_adapter.py -x --tb=short

Expected RED failure marker:
  ModuleNotFoundError: No module named 'app.src.skills'

GREEN target:
  - LLMAdapter class with __init__(base_url, api_key, model) and chat(system_prompt, user_prompt, max_tokens)
  - Uses httpx for HTTP calls to OpenAI-compatible /v1/chat/completions
  - Returns raw text; error handling with rate_limit/api_error/parse_error/content_filter categories
  - Environment variable config: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

Verify commands:
  pytest app/tests/unit/test_llm_adapter.py -x --tb=short
  pytest app/tests/unit/ -x --tb=short

Receipt path: receipts.json#T001

Done definition:
  - All unit tests pass
  - LLMAdapter.chat returns text on success
  - Error categories correctly classified
  - Env vars loaded with defaults

Escalation notes:
  - If httpx is not available, use urllib.request as fallback (no new dependency)
```

#### Risk: low
#### Dependencies: none

---

### T002: Script Generation Skill

- **Story/Scenario refs**: US-001 / S-001
- **AC refs**: AC-001
- **FR refs**: FR-001, FR-002
- **Design refs**: design.md "Skill 实现 > script_generation.py"
- **task_readiness**: `done`

#### Scope

- **Exact files in scope**:
  - NEW: `app/src/skills/script_generation.py`
  - NEW: `app/tests/unit/test_script_generation.py`
  - MODIFY: `app/src/workers/step_runner.py` (skill dispatch for script_generation)

#### Callsites / Reuse Checklist

- `app/src/workers/step_runner.py` — refactor if/elif to STEP_SKILLS dispatch; `run_script_generation` callsite
- `app/src/domain/models.py` — ArtifactType usage unchanged

#### Test Mapping

| Level | Test | Coverage |
|-------|------|----------|
| unit | `test_script_generation.py::test_generate_script_success` | Mock LLM, verify ScriptDraft schema (hook/body/call_to_action/estimated_duration_seconds) |
| unit | `test_script_generation.py::test_generate_script_topic_input` | Verify topic input handled |
| unit | `test_script_generation.py::test_generate_script_draft_input` | Verify draft input handled |
| unit | `test_script_generation.py::test_generate_script_parse_error` | Mock malformed JSON, verify raw response saved |
| unit | `test_script_generation.py::test_generate_script_llm_error` | Mock LLM failure, verify error handling |

#### Execution Block

```
Story / scenario refs: US-001 / S-001
Design refs: design.md "Skill 实现 > script_generation.py"

Exact files in scope:
  - app/src/skills/script_generation.py (NEW)
  - app/tests/unit/test_script_generation.py (NEW)
  - app/src/workers/step_runner.py (MODIFY — skill dispatch)

Callsites / reuse checklist:
  - step_runner.py: replace if/elif with STEP_SKILLS["script_generation"] = run_script_generation
  - Keep existing FAIL injection for smoke tests
  - Keep existing thread lock mechanism

RED command:
  pytest app/tests/unit/test_script_generation.py -x --tb=short

Expected RED failure marker:
  ModuleNotFoundError or ImportError for skills.script_generation

GREEN target:
  - run_script_generation(input_kind, input_text, llm_adapter) -> dict
  - Builds system prompt with JSON schema definition
  - Builds user prompt with input content
  - Calls LLM adapter, parses response as ScriptDraft
  - On parse failure: saves raw response, raises parse_error
  - Returns dict with hook, body, call_to_action, estimated_duration_seconds
  - Writes llm_raw + parsed_json artifacts
  - StepRunner refactored to use STEP_SKILLS dispatch dict

Verify commands:
  pytest app/tests/unit/test_script_generation.py -x --tb=short
  pytest app/tests/unit/test_step_runner.py -x --tb=short
  curl -sf http://localhost:8000/api/video-tasks | python3 -m json.tool

Receipt path: receipts.json#T002

Done definition:
  - All unit tests pass
  - Script generation produces valid ScriptDraft schema
  - Parse errors save raw response
  - StepRunner dispatches to script_generation skill
  - Existing step_runner tests still pass

Escalation notes:
  - LLM prompt design may need iteration for stable JSON output
```

#### Risk: medium (LLM JSON output stability)
#### Dependencies: T001

---

### T003: Storyboard Skill

- **Story/Scenario refs**: US-001 / S-002
- **AC refs**: AC-002
- **FR refs**: FR-003, FR-004
- **Design refs**: design.md "Skill 实现 > storyboard.py"
- **task_readiness**: `done`

#### Scope

- **Exact files in scope**:
  - NEW: `app/src/skills/storyboard.py`
  - NEW: `app/tests/unit/test_storyboard.py`
  - MODIFY: `app/src/workers/step_runner.py` (add storyboard to STEP_SKILLS + DEFAULT_STEP_KEYS)
  - MODIFY: `app/src/server/routes/video_tasks.py` (add storyboard to DEFAULT_STEP_KEYS)

#### Callsites / Reuse Checklist

- `app/src/workers/step_runner.py` — add `STEP_SKILLS["storyboard"] = run_storyboard`
- `app/src/server/routes/video_tasks.py` — add `"storyboard"` to `DEFAULT_STEP_KEYS`

#### Test Mapping

| Level | Test | Coverage |
|-------|------|----------|
| unit | `test_storyboard.py::test_generate_storyboard_success` | Mock LLM, verify StoryboardSegment list schema |
| unit | `test_storyboard.py::test_segments_have_required_fields` | Each segment has voiceover_text, visual_intent, expected_keywords, estimated_start_seconds, estimated_end_seconds |
| unit | `test_storyboard.py::test_segments_correspond_to_script` | Segment count matches script sections |
| unit | `test_storyboard.py::test_generate_storyboard_parse_error` | Mock malformed JSON, verify raw response saved |
| unit | `test_storyboard.py::test_generate_storyboard_llm_error` | Mock LLM failure, verify error handling |

#### Execution Block

```
Story / scenario refs: US-001 / S-002
Design refs: design.md "Skill 实现 > storyboard.py"

Exact files in scope:
  - app/src/skills/storyboard.py (NEW)
  - app/tests/unit/test_storyboard.py (NEW)
  - app/src/workers/step_runner.py (MODIFY)
  - app/src/server/routes/video_tasks.py (MODIFY)

Callsites / reuse checklist:
  - step_runner.py: add STEP_SKILLS["storyboard"] = run_storyboard
  - routes/video_tasks.py: DEFAULT_STEP_KEYS = ["script_generation", "storyboard", "review_script"]

RED command:
  pytest app/tests/unit/test_storyboard.py -x --tb=short

Expected RED failure marker:
  ModuleNotFoundError for skills.storyboard

GREEN target:
  - run_storyboard(script_draft: dict, llm_adapter) -> list[dict]
  - Builds prompt including full script content
  - Generates 3-8 StoryboardSegment items
  - Each segment: segment_index, voiceover_text, visual_intent, expected_keywords, estimated_start_seconds, estimated_end_seconds
  - Writes llm_raw + parsed_json artifacts
  - DEFAULT_STEP_KEYS updated to include "storyboard"

Verify commands:
  pytest app/tests/unit/test_storyboard.py -x --tb=short
  pytest app/tests/unit/test_step_runner.py -x --tb=short
  curl -sf http://localhost:8000/api/video-tasks | python3 -m json.tool

Receipt path: receipts.json#T003

Done definition:
  - All unit tests pass
  - Storyboard generates valid segments
  - DEFAULT_STEP_KEYS includes "storyboard"
  - StepRunner dispatches storyboard correctly

Escalation notes:
  - Storyboard prompt must include full script to ensure correspondence
```

#### Risk: medium (LLM JSON output stability)
#### Dependencies: T001

---

### T004: Review Script Skill

- **Story/Scenario refs**: US-001 / S-003
- **AC refs**: AC-003
- **FR refs**: FR-005, FR-006
- **Design refs**: design.md "Skill 实现 > review_script.py"
- **task_readiness**: `done`

#### Scope

- **Exact files in scope**:
  - NEW: `app/src/skills/review_script.py`
  - NEW: `app/tests/unit/test_review_script.py`
  - MODIFY: `app/src/workers/step_runner.py` (add review_script to STEP_SKILLS dispatch)

#### Callsites / Reuse Checklist

- `app/src/workers/step_runner.py` — add `STEP_SKILLS["review_script"] = run_review_script`
- Replace existing review_script if/elif branch with skill dispatch

#### Test Mapping

| Level | Test | Coverage |
|-------|------|----------|
| unit | `test_review_script.py::test_review_success` | Mock LLM, verify findings list with stage/severity/location_ref/message/suggested_fix |
| unit | `test_review_script.py::test_review_detects_issues` | Inject known issues, verify findings detect them |
| unit | `test_review_script.py::test_review_clean_pass` | Mock clean output, verify empty findings with pass status |
| unit | `test_review_script.py::test_review_parse_error` | Mock malformed JSON, verify raw response saved |
| unit | `test_review_script.py::test_findings_grounded` | Each finding has valid location_ref |

#### Execution Block

```
Story / scenario refs: US-001 / S-003
Design refs: design.md "Skill 实现 > review_script.py"

Exact files in scope:
  - app/src/skills/review_script.py (NEW)
  - app/tests/unit/test_review_script.py (NEW)
  - app/src/workers/step_runner.py (MODIFY)

Callsites / reuse checklist:
  - step_runner.py: add STEP_SKILLS["review_script"] = run_review_script
  - Replace existing review_script placeholder branch

RED command:
  pytest app/tests/unit/test_review_script.py -x --tb=short

Expected RED failure marker:
  ModuleNotFoundError for skills.review_script

GREEN target:
  - run_review_script(script_draft, storyboard_segments, llm_adapter) -> list[dict]
  - Builds prompt with full script + storyboard content
  - Returns list of ReviewFinding dicts
  - Each finding: stage, severity, location_ref, message, suggested_fix
  - Writes llm_raw + parsed_json + review artifacts

Verify commands:
  pytest app/tests/unit/test_review_script.py -x --tb=short
  pytest app/tests/unit/test_step_runner.py -x --tb=short
  curl -sf http://localhost:8000/api/video-tasks | python3 -m json.tool

Receipt path: receipts.json#T004

Done definition:
  - All unit tests pass
  - Review produces valid findings schema
  - Findings reference actual script/storyboard locations
  - Empty findings on clean output
  - StepRunner dispatches review_script correctly

Escalation notes:
  - Review prompt must include both script AND storyboard for full coverage
```

#### Risk: medium (LLM finding quality depends on prompt)
#### Dependencies: T001

---

### T005: Web 工作台升级（任务列表 + 可读产物展示）

- **Story/Scenario refs**: US-001 (S-001, S-002, S-003), US-002 (S-004)
- **AC refs**: AC-001, AC-002, AC-003, AC-004
- **FR refs**: FR-010, FR-011, FR-012, FR-013, FR-014
- **Design refs**: design.md "Web 工作台升级" + "任务列表 API" + "产物内容 API"
- **task_readiness**: `done`

#### Scope

- **Exact files in scope**:
  - MODIFY: `app/src/web/workbench.html` (major upgrade)
  - MODIFY: `app/src/web/workbench.js` (major rewrite)
  - MODIFY: `app/src/server/routes/video_tasks.py` (new endpoints)
  - MODIFY: `app/src/storage/sqlite.py` (add list_tasks)
  - NEW: `app/tests/unit/test_task_list.py`

#### Callsites / Reuse Checklist

- `app/src/web/workbench.html` — rewrite with hash routing SPA
- `app/src/web/workbench.js` — rewrite with task list + detail views
- `app/src/server/routes/video_tasks.py` — add GET /api/video-tasks + GET /api/video-tasks/{id}/artifacts/{aid}/content
- `app/src/storage/sqlite.py` — add list_tasks() method

#### Test Mapping

| Level | Test | Coverage |
|-------|------|----------|
| unit | `test_task_list.py::test_list_tasks_endpoint` | Verify list returns all tasks |
| unit | `test_task_list.py::test_list_tasks_ordered_by_created_at_desc` | Verify ordering |
| unit | `test_task_list.py::test_artifact_content_endpoint` | Verify content retrieval |
| unit | `test_task_list.py::test_artifact_content_not_found` | Verify 404 |
| unit | `test_task_list.py::test_store_list_tasks` | Verify SqliteStore.list_tasks() |

#### Delivery-Map (skeleton, to be expanded when ready)

```
Execution Block will be generated when task readiness advances to ready.

Required elements:
- Hash routing: #/ (task list), #/task/{id} (detail), #/new (create)
- Task list cards: ID, status badge, input summary, created_at
- Task detail: step cards, script rendering, storyboard table, review issue list
- API: GET /api/video-tasks, GET /api/video-tasks/{id}/artifacts/{aid}/content
- SqliteStore.list_tasks()
- Verify: curl -sf http://localhost:8000/api/video-tasks | python3 -m json.tool
```

#### Risk: medium (Web scope control)
#### Dependencies: T002, T003, T004

---

### T006: API 集成测试（S-001~S-004 全覆盖）

- **Story/Scenario refs**: S-001, S-002, S-003, S-004
- **AC refs**: AC-001, AC-002, AC-003, AC-004
- **FR refs**: FR-001–FR-006, FR-010
- **Design refs**: design.md "E2E Test Strategy"
- **task_readiness**: `done`

#### Scope

- **Exact files in scope**:
  - MODIFY: `app/tests/integration/test_api_video_tasks.py` (expand existing + add S-001~S-004 coverage)

#### Callsites / Reuse Checklist

- Extends existing integration tests from Feature 001

#### Test Mapping

| Level | Test | Coverage |
|-------|------|----------|
| integration | `test_script_generation_produces_artifact` (S-001) | POST task → verify script artifact with hook/body/CTA |
| integration | `test_storyboard_step_produces_segments` (S-002) | POST task → verify storyboard artifact with segments |
| integration | `test_review_step_produces_findings` (S-003) | POST task → verify review artifact with findings |
| integration | `test_task_list_endpoint` (S-004) | Create multiple tasks → GET list → verify all present |
| integration | `test_full_pipeline_e2e` | POST task → verify all 3 steps complete with artifacts |

#### Delivery-Map (skeleton)

```
Execution Block will be generated when task readiness advances to ready.

Required:
- Mock LLM responses for predictable assertions
- In-memory DB for isolation
- Each scenario covered by at least one integration test
- Blackbox verify command: pytest app/tests/integration/ -x
- Verify: curl -sf http://localhost:8000/api/video-tasks | python3 -m json.tool
```

#### Risk: low
#### Dependencies: T002, T003, T004, T005

---

### T007: Blackbox Smoke + AI Eval

- **Story/Scenario refs**: All
- **AC refs**: All
- **FR refs**: All boundary validation
- **Design refs**: design.md "E2E Test Strategy" + "AI Behavior Evaluation Strategy"
- **task_readiness**: `done`

#### Scope

- **Exact files in scope**:
  - MODIFY: `app/tests/blackbox/video_task_smoke.sh` (update for new steps + task list)
  - NEW: `app/evals/002/golden.jsonl`
  - NEW: `app/evals/run_002.py`
  - NEW: `app/eval-results/002.json` (generated at runtime)

#### Callsites / Reuse Checklist

- `app/tests/blackbox/video_task_smoke.sh` — extend for storyboard + task list verification
- `app/tests/blackbox/_common.sh` — reuse server start/stop helpers

#### Test Mapping

| Level | Test | Coverage |
|-------|------|----------|
| blackbox_smoke | `video_task_smoke.sh` | Full E2E: create task → verify all steps → check artifacts → task list |
| AI eval | `run_002.py` | Golden cases for script quality, storyboard structure, review detection |

#### Delivery-Map (skeleton)

```
Execution Block will be generated when task readiness advances to ready.

Testing Asset Map:
- Spec path: docs/01-features/002-ai-director-pipeline/feature.md
- RED command: bash app/tests/blackbox/video_task_smoke.sh
- Verify command: bash app/tests/blackbox/video_task_smoke.sh && echo "SMOKE PASSED"
- Runtime setup: start server with mock LLM or real LLM (env configurable)
- Artifact policy: preserve eval results

Eval Asset Map:
- Dataset path: app/evals/002/golden.jsonl
- Scorer/rubric: schema compliance (automated) + rubric scoring (manual)
- Eval RED command: python3 app/evals/run_002.py
- Verify command: python3 app/evals/run_002.py && echo "EVAL PASSED"
- Result artifact: app/eval-results/002.json
- Receipt: receipts.json#T007.eval_evidence
```

#### Risk: medium (eval design quality)
#### Dependencies: T006

---

## Testing Asset Map

| Scenario | E2E Level | Test Asset | Verify Command |
|----------|-----------|------------|----------------|
| S-001 | blackbox_smoke | `app/tests/integration/test_api_video_tasks.py` | `pytest app/tests/integration/ -x` |
| S-002 | blackbox_smoke | `app/tests/integration/test_api_video_tasks.py` | `pytest app/tests/integration/ -x` |
| S-003 | blackbox_smoke | `app/tests/integration/test_api_video_tasks.py` | `pytest app/tests/integration/ -x` |
| S-004 | blackbox_smoke | `app/tests/integration/test_api_video_tasks.py` | `pytest app/tests/integration/ -x` |
| All | blackbox_smoke | `app/tests/blackbox/video_task_smoke.sh` | `bash app/tests/blackbox/video_task_smoke.sh` |

## AI Behavior Evaluation Map

| Dimension | Dataset | Scorer | Eval Command | Result Artifact | Receipt |
|-----------|---------|--------|-------------|-----------------|---------|
| accuracy | `app/evals/002/golden.jsonl` | schema compliance + rubric | `python3 app/evals/run_002.py` | `app/eval-results/002.json` | receipts.json#T007.eval_evidence |
| relevance | same | segment-script correspondence | same | same | same |
| safety | same | reviewer flag check | same | same | same |
| format | same | Pydantic schema validation | same | same | same |
| grounding | same | location_ref validation | same | same | same |
