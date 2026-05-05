# Tasks: 素材两路径与失败分流（Feature 003）

> **Feature**: 003-material-dual-path
> **Implementation Mode**: extension
> **Complexity Tier**: standard
> **Created**: 2026-05-05
> **Created by**: /bewater-plan

## Constitution Compliance Notes

| Principle | Task Coverage | Notes |
|-----------|--------------|-------|
| P1: Evidence-First | 每个 task 有明确 test mapping | T001–T006 均有 unit/integration test |
| P2: User-Visible Slice | T005 Web UI + T006 integration 覆盖用户可见行为 | 素材状态面板 + 上传交互 |
| P3: Simplicity Over Speculation | 不引入消息队列/对象存储，复用现有架构 | httpx sync + ArtifactStore 扩展 |
| P4: Use Existing Architecture | 复用 FastAPI/SQLite/StepRunner | 不引入新框架 |
| P5: Boundary Validation | T006 integration + blackbox smoke | 覆盖下载/上传/状态转换完整链路 |
| P6: Workflow Over Editor | Web 只做素材状态展示和上传 | 不做素材编辑器 |
| P7: Reviewable Automation | material_status artifact 保留完整下载历史 | 每条链接结果可追溯 |
| P8: Rights-Aware Inputs | Web 保持素材权利声明 | 上传不改版权责任边界 |
| P9: Artifact-First | 素材文件和状态都写入 artifact | source_video + material_status |

---

## Task Summary

| ID | Title | Story | Scenarios | Test Level | Depends On | Risk | Readiness |
|----|-------|-------|-----------|------------|------------|------|-----------|
| T001 | Domain + Store + ArtifactStore foundation | US-001, US-002, US-003 | S-001, S-002, S-003 | unit | — | low | ready |
| T002 | Material fetch skill (download + error categorization) | US-001 | S-001 / AC-001 | unit | T001 | medium | ready |
| T003 | StepRunner integration + pipeline ordering | US-001, US-002 | S-001, S-002 / AC-001, AC-002 | unit | T001, T002 | medium | backlog |
| T004 | Upload API + pipeline resume | US-003 | S-003 / AC-003 | unit | T001, T003 | medium | backlog |
| T005 | Web material status + upload UI | US-001, US-002, US-003 | S-001, S-002, S-003 | blackbox_smoke | T004 | low | backlog |
| T006 | Integration tests + blackbox smoke | US-001, US-002, US-003 | S-001, S-002, S-003 / AC-001, AC-002, AC-003 | integration | T001–T005 | low | backlog |

---

## T001: Domain + Store + ArtifactStore Foundation

**Story**: US-001, US-002, US-003
**Scenario/AC**: S-001, S-002, S-003 / AC-001, AC-002, AC-003 (foundation)
**task_readiness**: ready

### Execution Block

- **Story / scenario refs**: Foundation for all scenarios — provides enum values and store methods needed by T002–T006
- **Design refs**: design.md § Domain Model Changes, § Data Model Changes
- **Exact files in scope**:
  - `app/src/domain/models.py` — add TaskStatus.waiting_for_material, ArtifactType.source_video/uploaded_video/material_status
  - `app/src/storage/sqlite.py` — add set_task_status method
  - `app/src/artifacts/store.py` — add write_file method, update list_task_artifacts for non-JSON
  - `app/pyproject.toml` — add httpx dependency
- **Callsites / reuse checklist**:
  - TaskStatus.waiting_for_material: consumed by step_runner.py, routes/video_tasks.py
  - ArtifactType.source_video/uploaded_video/material_status: consumed by step_runner.py, routes
  - ArtifactStore.write_file: consumed by material_fetch skill, upload API
  - SqliteStore.set_task_status: consumed by step_runner.py, upload route
- **RED command**: `cd app && python -m pytest tests/unit/test_domain_models.py tests/unit/test_sqlite_store.py tests/unit/test_artifact_store.py -x -q`
- **Expected RED failure marker**: `FAILED` — tests reference `TaskStatus.waiting_for_material`, `ArtifactType.source_video`, `ArtifactStore.write_file`, `SqliteStore.set_task_status` which do not yet exist
- **GREEN target**:
  1. Add `waiting_for_material = "waiting_for_material"` to TaskStatus enum
  2. Add `source_video`, `uploaded_video`, `material_status` to ArtifactType enum
  3. Add `set_task_status(task_id, status)` to SqliteStore — updates status + updated_at
  4. Add `write_file(task_id, step_key, artifact_type, filename, content: bytes)` to ArtifactStore
  5. Update `list_task_artifacts` to glob both `*.json` and video extensions
  6. Add `httpx` to pyproject.toml dependencies
- **Verify commands**:
  - `cd app && python -m pytest tests/unit/test_domain_models.py tests/unit/test_sqlite_store.py tests/unit/test_artifact_store.py -x -q`
  - `cd app && python -m pytest tests/unit/ -x -q` (regression)
- **Receipt path**: `docs/01-features/003-material-dual-path/receipts.json#T001`
- **Done definition**: All new enum values accessible; `set_task_status` updates DB; `write_file` creates binary file in task dir; existing tests still pass
- **Escalation notes**: If list_task_artifacts change breaks existing consumers, verify `*.json` glob behavior is preserved as subset of new glob

---

## T002: Material Fetch Skill (Download + Error Categorization)

**Story**: US-001
**Scenario/AC**: S-001 / AC-001
**task_readiness**: ready

### Execution Block

- **Story / scenario refs**: S-001 — 系统自动下载素材链接并展示获取状态
- **Design refs**: design.md § US-001, § 下载错误分类规则, § 支持的文件格式
- **Exact files in scope**:
  - `app/src/skills/material_fetch.py` — new file: download logic + error categorization
  - `app/tests/unit/test_material_fetch.py` — new test file
- **Callsites / reuse checklist**:
  - `run_material_fetch()` called by StepRunner._run_material_fetch (T003)
  - Uses `ArtifactStore.write_file` from T001
  - Uses `ALLOWED_EXTENSIONS`, `ALLOWED_CONTENT_TYPES`, `MAX_FILE_SIZE`, `DOWNLOAD_TIMEOUT` module constants
- **RED command**: `cd app && python -m pytest tests/unit/test_material_fetch.py -x -q`
- **Expected RED failure marker**: `FAILED` — test file imports `app.src.skills.material_fetch` which does not exist
- **GREEN target**:
  1. Create `app/src/skills/material_fetch.py`
  2. Define `MaterialFetchResult` dataclass: url, status, failure_category, failure_message, storage_ref, file_size, content_type
  3. Define constants: ALLOWED_EXTENSIONS, ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE, DOWNLOAD_TIMEOUT
  4. Implement `run_material_fetch(source_links, artifact_store, task_id)`:
     - For each URL: try httpx sync GET with timeout
     - On success: validate Content-Type + extension, check size, write via artifact_store.write_file
     - On error: categorize into unreachable/timeout/unsupported_format/size_exceeded/platform_restriction
     - Return list of MaterialFetchResult
  5. Implement error categorization helper: map httpx exceptions to failure categories
  6. Implement platform_restriction detection: HTTP 200 but body < 1KB and no video Content-Type
- **Verify commands**:
  - `cd app && python -m pytest tests/unit/test_material_fetch.py -x -q`
  - Test cases must cover: successful download, unreachable URL, timeout, wrong format, oversized file, platform restriction, empty source_links
- **Receipt path**: `docs/01-features/003-material-dual-path/receipts.json#T002`
- **Done definition**: Each error category has a test case; successful download writes file via store; empty links returns empty list; mock httpx for all tests
- **Escalation notes**: If httpx not yet in dependencies (T001 should have added it), add explicitly. If ArtifactStore.write_file not yet available, mock it in tests.

---

## T003: StepRunner Integration + Pipeline Ordering

**Story**: US-001, US-002
**Scenario/AC**: S-001, S-002 / AC-001, AC-002
**Depends on**: T001, T002
**Risk**: medium — modifies StepRunner dispatch and create_video_task pipeline logic
**task_readiness**: backlog

### Delivery Map

- **Design refs**: design.md § US-001 Step 4, § Pipeline Ordering, § Task Status 状态机
- **Files in scope**:
  - `app/src/workers/step_runner.py` — add _run_material_fetch handler, register in STEP_SKILLS
  - `app/src/server/routes/video_tasks.py` — update DEFAULT_STEP_KEYS, update create_video_task logic
  - `app/tests/unit/test_step_runner.py` — add material_fetch tests
- **Test mapping**: unit — step dispatch, material_fetch handler, pipeline ordering
- **Callsites / reuse checklist**:
  - STEP_SKILLS dict: add "material_fetch" entry
  - _run_skill method: add material_fetch branch
  - DEFAULT_STEP_KEYS: prepend "material_fetch"
  - create_video_task: run material_fetch first, check task status before continuing
- **Done definition**:
  - material_fetch registered in STEP_SKILLS and dispatched correctly
  - _run_material_fetch reads source_links, calls skill, writes artifacts, handles all-failed → waiting_for_material
  - create_video_task runs material_fetch first, skips remaining steps if waiting_for_material
  - No source_links → material_fetch step completed immediately

---

## T004: Upload API + Pipeline Resume

**Story**: US-003
**Scenario/AC**: S-003 / AC-003
**Depends on**: T001, T003
**Risk**: medium — new API endpoint with file upload security concerns
**task_readiness**: backlog

### Delivery Map

- **Design refs**: design.md § US-003, § 素材上传 API, § Pipeline 触发机制
- **Files in scope**:
  - `app/src/server/routes/video_tasks.py` — add upload_material endpoint
  - `app/src/server/schemas.py` — add UploadMaterialResponse
  - `app/tests/integration/test_api_video_tasks.py` — add upload tests
- **Test mapping**: unit — schema validation, file type/size checks; integration — upload → status change → pipeline resume
- **Callsites / reuse checklist**:
  - Upload endpoint validates: task exists + waiting_for_material, file extension, file size
  - On success: write file via store, add uploaded_video artifact, set step completed, set task running, trigger remaining steps
  - UploadMaterialResponse schema: accepted, artifact_id, filename
- **Done definition**:
  - Upload to non-waiting_for_material task returns 409
  - Invalid file type returns 422
  - Valid upload resumes pipeline (script → storyboard → review)
  - Security: filename sanitized, size enforced

---

## T005: Web Material Status + Upload UI

**Story**: US-001, US-002, US-003
**Scenario/AC**: S-001, S-002, S-003 / AC-001, AC-002, AC-003
**Depends on**: T004
**Risk**: low — vanilla HTML/JS, consistent with existing workbench
**task_readiness**: backlog

### Delivery Map

- **Design refs**: design.md § US-002 Web 素材状态面板, § 失败原因中文映射
- **Files in scope**:
  - `app/src/web/workbench.html` — add material status section and upload form
  - `app/src/web/workbench.js` — add material status rendering, upload interaction, progress feedback
- **Test mapping**: blackbox_smoke — verify material status renders, upload button appears when waiting_for_material
- **Callsites / reuse checklist**:
  - Read material_status artifact for rendering per-link status
  - FAILURE_CATEGORY_LABELS for Chinese error messages
  - Upload uses FormData + fetch to POST /api/video-tasks/{id}/materials
  - Reuse existing task detail rendering patterns
- **Done definition**:
  - Task detail page shows material status panel with per-link status
  - Failed links show Chinese failure reason
  - Upload button appears when task is waiting_for_material
  - Upload completes → page refreshes with updated status
  - No XSS in rendered URLs or filenames

---

## T006: Integration Tests + Blackbox Smoke

**Story**: US-001, US-002, US-003
**Scenario/AC**: S-001, S-002, S-003 / AC-001, AC-002, AC-003
**Depends on**: T001–T005
**Risk**: low
**task_readiness**: backlog

### Delivery Map

- **Design refs**: design.md § E2E Test Strategy
- **Files in scope**:
  - `app/tests/integration/test_api_video_tasks.py` — add material scenarios
  - `app/tests/blackbox/video_task_smoke.sh` — update with source_links scenario
- **Test mapping**: integration — full pipeline with material fetch; blackbox_smoke — end-to-end with source links
- **Coverage Matrix**:

| Scenario | Task | Test Type | Test File |
|----------|------|-----------|-----------|
| S-001 素材下载状态 | T002, T003 | unit + integration | test_material_fetch.py, test_api_video_tasks.py |
| S-002 全部失败→waiting | T003 | unit + integration | test_step_runner.py, test_api_video_tasks.py |
| S-003 上传→继续 | T004 | integration | test_api_video_tasks.py |

- **Done definition**:
  - S-001: Create task with mock URL → material_fetch produces status artifact with per-link results
  - S-002: Create task with all-failing URLs → task status = waiting_for_material
  - S-003: Upload file to waiting task → task resumes, pipeline completes
  - Blackbox smoke: source_links field in create request, material status in response
  - All existing tests still pass

---

## Dependency Graph

```text
T001 (Domain + Store + ArtifactStore)
 ├── T002 (Material Fetch Skill)
 │    └── T003 (StepRunner + Pipeline)
 │         └── T004 (Upload API)
 │              └── T005 (Web UI)
 │                   └── T006 (Integration Tests)
 └──────────────────────────────────────────T006
```

## Parallel Groups

| Group | Tasks | Rationale |
|-------|-------|-----------|
| A | T001, T002 | T002 can be developed with mocked ArtifactStore; both have isolated test files |

---

## Coverage Matrix

| Scenario | AC | T001 | T002 | T003 | T004 | T005 | T006 |
|----------|-----|------|------|------|------|------|------|
| S-001 素材下载状态 | AC-001 | foundation | ✅ unit | ✅ unit | — | ✅ display | ✅ int |
| S-002 全部失败→暂停 | AC-002 | foundation | — | ✅ unit | — | ✅ display | ✅ int |
| S-003 上传→继续 | AC-003 | foundation | — | — | ✅ unit+int | ✅ upload UI | ✅ int |

---

## Testing Asset Map

| Asset | Type | Path | Status |
|-------|------|------|--------|
| Material fetch unit tests | unit | `app/tests/unit/test_material_fetch.py` | planned |
| Domain model unit tests | unit | `app/tests/unit/test_domain_models.py` | planned |
| Step runner material tests | unit | `app/tests/unit/test_step_runner.py` | extend existing |
| Integration tests | integration | `app/tests/integration/test_api_video_tasks.py` | extend existing |
| Blackbox smoke | blackbox_smoke | `app/tests/blackbox/video_task_smoke.sh` | extend existing |
