---
feature_id: "004"
tasks_for: 媒体管线核心（配音 + 素材处理 + 字幕 + 合成）
created_at: 2026-05-05
complexity_tier: deep
implementation_mode: extension
---

# Tasks: 004-media-pipeline-core

## Reuse Analysis (extension mode)

| Existing Module | Reuse Pattern | Changes Needed |
|----------------|---------------|----------------|
| `step_runner.py` STEP_SKILLS + _run_* | 新增 5 个 skill 注册和 _run_* 方法 | Add imports, registry entries, 5 new methods |
| `step_runner.py` _read_latest_artifact_payload | 直接复用读取前置步骤 artifact | No changes |
| `artifact_store.py` write_file / write_json | 复用写入，扩展允许的文件类型 | Add .mp3/.srt to ALLOWED_EXTENSIONS |
| `video_tasks.py` DEFAULT_STEP_KEYS | 扩展管线步骤列表 | Append 5 new step keys |
| `video_tasks.py` create_video_task | 复用同步执行模式 | Extend step execution loop |
| `video_tasks.py` upload_material | 复用 resume 模式 | Extend resume step list |
| `workbench.js` renderProductSections | 复用 artifact 分组渲染模式 | Add final_video section |
| `models.py` ArtifactType | 扩展枚举 | Add 4 new types |

## Callsite Inventory

| Changed Interface | All Callsites |
|-------------------|---------------|
| `ArtifactType` enum | step_runner.py, video_tasks.py, test_step_runner.py, test_domain_models_003.py |
| `ALLOWED_EXTENSIONS` | store.py write_file, list_task_artifacts |
| `STEP_SKILLS` dict | step_runner.py run_step |
| `_run_skill` dispatch | step_runner.py _run_skill |
| `DEFAULT_STEP_KEYS` | video_tasks.py create_video_task, upload_material |
| `renderProductSections` | workbench.js renderTaskDetail |

## Regression Coverage

- `test_step_runner.py`: step dispatch + _run_* methods for existing skills
- `test_api_video_tasks.py`: API create/get/retry/list endpoints
- `test_artifacts.py`: artifact store write/read
- `test_material_fetch.py`: material download logic
- All existing tests must pass after each task

---

## Task List

### T001: Infrastructure — ArtifactType + ArtifactStore + FFmpeg utils

- **story_id**: US-001, US-002 (shared)
- **scenario/AC refs**: Infrastructure for S-001~S-006
- **description**: Extend ArtifactType with 4 new types, extend ArtifactStore for audio/subtitle files, create FFmpeg utility module
- **files in scope**:
  - `app/src/domain/models.py` — add ArtifactType.audio/clip/subtitle/final_video
  - `app/src/artifacts/store.py` — extend ALLOWED_EXTENSIONS, _MEDIA_EXTENSIONS for listing
  - `app/src/media/__init__.py` — new package
  - `app/src/media/ffmpeg_utils.py` — check_ffmpeg_available, probe_duration, run_ffmpeg
  - `app/tests/unit/test_domain_models_004.py` — new
  - `app/tests/unit/test_artifact_store_004.py` — new
  - `app/tests/unit/test_ffmpeg_utils.py` — new
- **dependencies**: none
- **risk**: low — enum and extension changes are backward-compatible
- **task_readiness**: done
- **test mapping**: unit
- **parallel_group**: A

#### Execution Block

- **Story / scenario refs**: US-001 + US-002 shared infrastructure
- **Design refs**: design.md "Shared Cross-Story Concerns" — ArtifactType Extension, ArtifactStore Extension, FFmpeg Dependency
- **Exact files in scope**: models.py, store.py, media/__init__.py, media/ffmpeg_utils.py
- **Callsites / reuse checklist**:
  - ArtifactType: verify existing callsites (step_runner.py:8, video_tasks.py:8) still resolve
  - ALLOWED_EXTENSIONS: verify write_file still validates, list_task_artifacts still enumerates
- **RED command**:
  ```bash
  python -m pytest app/tests/unit/test_domain_models_004.py app/tests/unit/test_artifact_store_004.py app/tests/unit/test_ffmpeg_utils.py -x -q
  ```
- **Expected RED failure marker**: ImportError (media package) / AssertionError (missing enum values / extension rejection)
- **GREEN target**:
  1. Add `audio`, `clip`, `subtitle`, `final_video` to `ArtifactType` enum
  2. Add `.mp3`, `.wav`, `.srt` to `ALLOWED_EXTENSIONS` in store.py
  3. Update `_VIDEO_EXTENSIONS` → `_MEDIA_EXTENSIONS` with `.mp3`, `.srt` for listing
  4. Create `app/src/media/__init__.py` (empty)
  5. Create `app/src/media/ffmpeg_utils.py` with `check_ffmpeg_available()`, `probe_duration()`, `run_ffmpeg()`
- **Verify commands**:
  ```bash
  python -m pytest app/tests/unit/ -x -q
  ```
- **Receipt path**: `docs/01-features/004-media-pipeline-core/receipts/T001.json`
- **Done definition**: All 3 new test files green + all existing unit tests green
- **Escalation notes**: If ArtifactType changes break existing callsites, update references in step_runner.py and video_tasks.py

---

### T002: Voiceover skill + StepRunner integration

- **story_id**: US-001
- **scenario/AC refs**: S-001 / AC-001
- **description**: Implement voiceover skill using edge-tts with per-segment TTS generation and word boundary timing capture. Integrate with StepRunner.
- **files in scope**:
  - `app/src/skills/voiceover.py` — new skill
  - `app/src/workers/step_runner.py` — add STEP_SKILLS entry + _run_voiceover
  - `app/tests/unit/test_voiceover.py` — new
- **dependencies**: T001
- **risk**: medium — edge-tts is async, needs asyncio.run wrapper; external API dependency
- **task_readiness**: done
- **test mapping**: unit (mock edge-tts)
- **parallel_group**: B

#### Execution Block

- **Story / scenario refs**: US-001 / S-001 / AC-001
- **Design refs**: design.md "US-001 — voiceover skill", D006
- **Exact files in scope**: skills/voiceover.py, workers/step_runner.py
- **Callsites / reuse checklist**:
  - StepRunner: add import + STEP_SKILLS["voiceover"] = run_voiceover
  - _run_skill: add `if step_key == "voiceover": return self._run_voiceover(...)` dispatch
  - Follow _run_storyboard pattern for reading upstream artifact
- **RED command**:
  ```bash
  python -m pytest app/tests/unit/test_voiceover.py -x -q
  ```
- **Expected RED failure marker**: ImportError (voiceover module)
- **GREEN target**:
  1. Create `voiceover.py` with `run_voiceover(storyboard_segments, artifact_store, task_id) -> dict`
  2. Use `asyncio.run()` wrapper for edge-tts async API
  3. Per-segment TTS with WordBoundary capture
  4. FFmpeg concat for full voiceover
  5. Return timing_data dict (segments with duration + word_boundaries)
  6. Add `_run_voiceover` to StepRunner: read storyboard artifact → call skill → write audio + timing artifacts
- **Verify commands**:
  ```bash
  python -m pytest app/tests/unit/test_voiceover.py app/tests/unit/test_step_runner.py -x -q
  ```
- **Receipt path**: `docs/01-features/004-media-pipeline-core/receipts/T002.json`
- **Done definition**: Voiceover unit tests green + step_runner tests green (existing + new voiceover dispatch)
- **Escalation notes**: edge-tts API instability in CI — mock all edge-tts calls in unit tests; integration test uses real edge-tts

---

### T003: Material extract skill + StepRunner integration

- **story_id**: US-001
- **scenario/AC refs**: S-002 / AC-002
- **description**: Implement material_extract skill that cuts source videos into fixed-duration clips using FFmpeg. Integrate with StepRunner.
- **files in scope**:
  - `app/src/skills/material_extract.py` — new skill
  - `app/src/workers/step_runner.py` — add STEP_SKILLS entry + _run_material_extract
  - `app/tests/unit/test_material_extract.py` — new
- **dependencies**: T001
- **risk**: low — FFmpeg subprocess calls, well-tested pattern
- **task_readiness**: done
- **test mapping**: unit (mock FFmpeg subprocess)
- **parallel_group**: B

#### Execution Block

- **Story / scenario refs**: US-001 / S-002 / AC-002
- **Design refs**: design.md "US-001 — material_extract skill", D008
- **Exact files in scope**: skills/material_extract.py, workers/step_runner.py
- **Callsites / reuse checklist**:
  - StepRunner: add import + STEP_SKILLS entry
  - _run_material_fetch pattern: skill takes artifact_store for file writing
  - ffmpeg_utils: use check_ffmpeg_available, probe_duration
- **RED command**:
  ```bash
  python -m pytest app/tests/unit/test_material_extract.py -x -q
  ```
- **Expected RED failure marker**: ImportError
- **GREEN target**:
  1. Create `material_extract.py` with `run_material_extract(source_video_refs, artifact_store, task_id) -> dict`
  2. Probe source video durations via ffprobe
  3. Cut into ~5s clips with ffmpeg -ss/-to -c copy
  4. Return clip_manifest dict with per-clip metadata
  5. Handle no-source-videos case (return empty manifest)
  6. Add `_run_material_extract` to StepRunner: read source_video artifacts → call skill → write clip artifacts + manifest
- **Verify commands**:
  ```bash
  python -m pytest app/tests/unit/test_material_extract.py app/tests/unit/test_step_runner.py -x -q
  ```
- **Receipt path**: `docs/01-features/004-media-pipeline-core/receipts/T003.json`
- **Done definition**: Material extract unit tests green + step_runner tests green
- **Escalation notes**: None expected

---

### T004: Material match skill + StepRunner integration

- **story_id**: US-001
- **scenario/AC refs**: S-003 / AC-003
- **description**: Implement duration-based matching algorithm that assigns clips to voiceover segments. Integrate with StepRunner.
- **files in scope**:
  - `app/src/skills/material_match.py` — new skill
  - `app/src/workers/step_runner.py` — add STEP_SKILLS entry + _run_material_match
  - `app/tests/unit/test_material_match.py` — new
- **dependencies**: T002 (needs voiceover timing schema)
- **risk**: low — pure computation, no external dependencies
- **task_readiness**: done
- **test mapping**: unit
- **parallel_group**: C

#### Execution Block

- **Story / scenario refs**: US-001 / S-003 / AC-003
- **Design refs**: design.md "US-001 — material_match skill", D008
- **Exact files in scope**: skills/material_match.py, workers/step_runner.py
- **Callsites / reuse checklist**:
  - StepRunner: add import + STEP_SKILLS entry + _run_material_match
  - _run_material_match reads voiceover_timing + clip_manifest from parsed_json artifacts
- **RED command**:
  ```bash
  python -m pytest app/tests/unit/test_material_match.py -x -q
  ```
- **Expected RED failure marker**: ImportError
- **GREEN target**:
  1. Create `material_match.py` with `run_material_match(voiceover_timing, clip_manifest) -> dict`
  2. Sequential duration-based assignment with clip looping
  3. Handle empty clips (fallback_mode=true)
  4. Add `_run_material_match` to StepRunner
- **Verify commands**:
  ```bash
  python -m pytest app/tests/unit/test_material_match.py app/tests/unit/test_step_runner.py -x -q
  ```
- **Receipt path**: `docs/01-features/004-media-pipeline-core/receipts/T004.json`
- **Done definition**: Material match unit tests green + step_runner tests green
- **Escalation notes**: None expected

---

### T005: Subtitle skill + StepRunner integration

- **story_id**: US-001
- **scenario/AC refs**: S-004 / AC-004
- **description**: Implement subtitle generation from edge-tts word boundary timing. Convert timing data to SRT format. Integrate with StepRunner.
- **files in scope**:
  - `app/src/skills/subtitle.py` — new skill
  - `app/src/workers/step_runner.py` — add STEP_SKILLS entry + _run_subtitle
  - `app/tests/unit/test_subtitle.py` — new
- **dependencies**: T002 (needs voiceover timing data)
- **risk**: low — deterministic conversion, edge-tts timing quality is the only variable
- **task_readiness**: done
- **test mapping**: unit
- **parallel_group**: C

#### Execution Block

- **Story / scenario refs**: US-001 / S-004 / AC-004
- **Design refs**: design.md "US-001 — subtitle skill", D007
- **Exact files in scope**: skills/subtitle.py, workers/step_runner.py
- **Callsites / reuse checklist**:
  - StepRunner: add import + STEP_SKILLS entry + _run_subtitle
  - Reads voiceover_timing parsed_json from voiceover step
  - Writes .srt file via artifact_store.write_file (bytes-encoded text)
- **RED command**:
  ```bash
  python -m pytest app/tests/unit/test_subtitle.py -x -q
  ```
- **Expected RED failure marker**: ImportError
- **GREEN target**:
  1. Create `subtitle.py` with `run_subtitle(voiceover_timing, artifact_store, task_id) -> dict`
  2. Convert word boundaries to SRT entries (one per segment, split if >10s)
  3. Format SRT with millisecond precision
  4. Write .srt file via artifact_store
  5. Add `_run_subtitle` to StepRunner
- **Verify commands**:
  ```bash
  python -m pytest app/tests/unit/test_subtitle.py app/tests/unit/test_step_runner.py -x -q
  ```
- **Receipt path**: `docs/01-features/004-media-pipeline-core/receipts/T005.json`
- **Done definition**: Subtitle unit tests green + step_runner tests green
- **Escalation notes**: If word_boundaries are empty, fallback to segment-level timing from storyboard

---

### T006: Video compose skill + StepRunner integration

- **story_id**: US-001
- **scenario/AC refs**: S-005 / AC-005
- **description**: Implement FFmpeg-based video composition with clip concatenation + audio overlay + subtitle burn-in. Support solid color fallback. Integrate with StepRunner.
- **files in scope**:
  - `app/src/skills/video_compose.py` — new skill
  - `app/src/workers/step_runner.py` — add STEP_SKILLS entry + _run_video_compose
  - `app/tests/unit/test_video_compose.py` — new
- **dependencies**: T002, T003, T004, T005
- **risk**: high — FFmpeg complex filter graph, environment differences, long compose time
- **task_readiness**: done
- **test mapping**: unit (mock FFmpeg)
- **parallel_group**: D

#### Execution Block

- **Story / scenario refs**: US-001 / S-005 / AC-005
- **Design refs**: design.md "US-001 — video_compose skill", D009, D010
- **Exact files in scope**: skills/video_compose.py, workers/step_runner.py
- **Callsites / reuse checklist**:
  - StepRunner: add import + STEP_SKILLS entry + _run_video_compose
  - Reads matched_segments + voiceover_timing + subtitle artifact + clip_manifest
  - Uses ffmpeg_utils for subprocess execution
- **RED command**:
  ```bash
  python -m pytest app/tests/unit/test_video_compose.py -x -q
  ```
- **Expected RED failure marker**: ImportError
- **GREEN target**:
  1. Create `video_compose.py` with `run_video_compose(matched_segments, voiceover_timing, subtitle_ref, clip_manifest, artifact_store, task_id) -> dict`
  2. Normal mode: build concat input from matched_segments, run FFmpeg concat + audio + subtitle burn-in
  3. Fallback mode: FFmpeg color source + audio + subtitle
  4. Write output.mp4 + compose_log.json
  5. Add `_run_video_compose` to StepRunner
- **Verify commands**:
  ```bash
  python -m pytest app/tests/unit/test_video_compose.py app/tests/unit/test_step_runner.py -x -q
  ```
- **Receipt path**: `docs/01-features/004-media-pipeline-core/receipts/T006.json`
- **Done definition**: Video compose unit tests green + step_runner tests green
- **Escalation notes**: FFmpeg filter syntax is environment-sensitive; verify on macOS and Linux. If subtitle burn-in fails due to font, fall back to default font.

---

### T007: Pipeline orchestration + API file serving

- **story_id**: US-001, US-002
- **scenario/AC refs**: FR-010, FR-011, AC-006 (partial)
- **description**: Extend DEFAULT_STEP_KEYS, update pipeline execution in create_video_task and upload_material. Add GET endpoint for serving binary artifact files (video/audio streaming).
- **files in scope**:
  - `app/src/server/routes/video_tasks.py` — extend DEFAULT_STEP_KEYS, pipeline logic, add /file endpoint
  - `app/src/server/schemas.py` — add FileResponse types if needed
  - `app/tests/unit/test_pipeline_orchestration.py` — new
  - `app/tests/integration/test_api_video_tasks.py` — extend
- **dependencies**: T006
- **risk**: medium — changes core pipeline execution, regression risk
- **task_readiness**: done
- **test mapping**: unit + integration
- **parallel_group**: E

#### Execution Block

- **Story / scenario refs**: US-001 / FR-010, FR-011 + US-002 / S-006 (API part)
- **Design refs**: design.md "Pipeline Orchestration", "US-002 — Web video preview and download"
- **Exact files in scope**: routes/video_tasks.py, schemas.py
- **Callsites / reuse checklist**:
  - DEFAULT_STEP_KEYS: update in create_video_task and upload_material
  - create_video_task: extend step execution loop to include all 9 steps
  - upload_material: extend resume step list to include all steps after material_fetch
  - get_artifact_content: add .srt to readable extensions
- **RED command**:
  ```bash
  python -m pytest app/tests/unit/test_pipeline_orchestration.py app/tests/integration/test_api_video_tasks.py -x -q
  ```
- **Expected RED failure marker**: AssertionError (step count mismatch, endpoint not found)
- **GREEN target**:
  1. Extend DEFAULT_STEP_KEYS to 9 entries
  2. Replace hardcoded step list in create_video_task with DEFAULT_STEP_KEYS[1:] loop
  3. Replace hardcoded resume list in upload_material with dynamic resume from failed step
  4. Add `GET /{task_id}/artifacts/{artifact_id}/file` endpoint using FastAPI FileResponse
  5. Add .srt to non-binary extensions in get_artifact_content
- **Verify commands**:
  ```bash
  python -m pytest app/tests/unit/ app/tests/integration/ -x -q
  ```
- **Receipt path**: `docs/01-features/004-media-pipeline-core/receipts/T007.json`
- **Done definition**: Pipeline orchestration tests green + all API tests green + all existing tests green
- **Escalation notes**: Regression risk — verify all existing step_runner and API tests still pass. If pipeline execution order changes break retry logic, review retry flow.

---

### T008: Web workbench video preview + download

- **story_id**: US-002
- **scenario/AC refs**: S-006 / AC-006
- **description**: Add video player and download button to workbench when final_video artifact exists. Show audio/subtitle/clip artifact info for media steps.
- **files in scope**:
  - `app/src/web/workbench.html` — add video player CSS
  - `app/src/web/workbench.js` — add video section rendering + artifact display for media steps
  - `app/tests/unit/test_workbench_smoke.py` — new (or manual smoke)
- **dependencies**: T007
- **risk**: low — UI extension only
- **task_readiness**: done
- **test mapping**: blackbox_smoke
- **parallel_group**: F

#### Execution Block

- **Story / scenario refs**: US-002 / S-006 / AC-006
- **Design refs**: design.md "US-002 — Web video preview and download", "Entry Points / Discovery Path"
- **Exact files in scope**: web/workbench.html, web/workbench.js
- **Callsites / reuse checklist**:
  - renderProductSections: add final_video section following script/storyboard pattern
  - renderArtifactContent: add cases for voiceover, material_extract, material_match, subtitle, video_compose steps
  - Discovery: video section only renders when final_video artifact exists
- **RED command**:
  ```bash
  # Smoke: verify workbench page loads
  curl -s http://localhost:8000/workbench.html | grep -q "video"
  ```
- **Expected RED failure marker**: grep exit code 1 (no video-related HTML)
- **GREEN target**:
  1. In renderProductSections: detect final_video artifact → render `<video controls>` + download link
  2. In renderArtifactContent: add rendering for media step artifacts (timing data, clip manifest, etc.)
  3. Video player src points to `/api/video-tasks/{id}/artifacts/{artId}/file`
  4. Download link uses same endpoint with `download` attribute
  5. Ensure step cards show all 9 steps (not just original 4)
- **Verify commands**:
  ```bash
  python -m pytest app/tests/ -x -q
  ```
- **Receipt path**: `docs/01-features/004-media-pipeline-core/receipts/T008.json`
- **Done definition**: Workbench renders video player when final_video exists; all existing tests pass
- **Escalation notes**: None expected

---

### T009: E2E integration test

- **story_id**: US-001 + US-002
- **scenario/AC refs**: S-001~S-006
- **description**: End-to-end test verifying full pipeline: submit task → pipeline completes → final_video artifact exists → API serves video → web displays player. Includes no-source-videos fallback scenario.
- **files in scope**:
  - `app/tests/integration/test_media_pipeline.py` — new
  - `app/tests/fixtures/test_video.mp4` — test asset (if not exists)
- **dependencies**: T007, T008
- **risk**: medium — depends on FFmpeg being available in test environment
- **task_readiness**: done
- **test mapping**: formal_e2e
- **parallel_group**: G

#### Execution Block

- **Story / scenario refs**: US-001 S-001~S-005 + US-002 S-006
- **Design refs**: design.md "E2E Test Strategy"
- **Exact files in scope**: tests/integration/test_media_pipeline.py, tests/fixtures/
- **Callsites / reuse checklist**:
  - Uses TestClient for API calls
  - Mocks edge-tts to avoid external API dependency
  - Uses real FFmpeg (skip if not available)
- **RED command**:
  ```bash
  python -m pytest app/tests/integration/test_media_pipeline.py -x -q
  ```
- **Expected RED failure marker**: ImportError or FileNotFoundError (test file / fixture missing)
- **GREEN target**:
  1. Test: submit task with topic → verify all 9 steps complete → verify final_video artifact exists
  2. Test: submit task with no source links → verify fallback mode → verify final_video exists
  3. Test: GET artifact file endpoint → verify Content-Type video/mp4
  4. Mock edge-tts in all E2E tests
  5. Use real FFmpeg, skip tests if unavailable
- **Verify commands**:
  ```bash
  python -m pytest app/tests/integration/test_media_pipeline.py -x -q
  python -m pytest app/tests/ -x -q
  ```
- **Receipt path**: `docs/01-features/004-media-pipeline-core/receipts/T009.json`
- **Done definition**: E2E tests green (or properly skipped when FFmpeg unavailable) + full test suite green
- **Escalation notes**: If FFmpeg not available in CI, mark E2E as skip with clear reason. These tests MUST pass in local dev environment.

---

## Coverage Matrix

| Scenario | AC | Task | Test Level | Verification |
|----------|----|----|------------|-------------|
| S-001: 生成配音 | AC-001 | T002 | unit (mock edge-tts) | timing_data structure + audio artifact |
| S-002: 切出片段 | AC-002 | T003 | unit (mock FFmpeg) | clip_manifest + clip artifacts |
| S-003: 配音匹配素材 | AC-003 | T004 | unit (pure computation) | matched_segments with correct assignments |
| S-004: 生成字幕 | AC-004 | T005 | unit | SRT format + timing alignment |
| S-005: 合成视频 | AC-005 | T006 | unit (mock FFmpeg) + E2E (T009) | final_video artifact + compose_log |
| S-006: Web 预览下载 | AC-006 | T008 + T009 | blackbox_smoke + E2E | video tag + download link + file endpoint |

## Testing Asset Map

| Asset | Path | Used By | Runtime Setup |
|-------|------|---------|---------------|
| Test video fixture | `app/tests/fixtures/test_video.mp4` | T009 (E2E) | 3-5s MP4, committed to repo |
| Mock edge-tts | Unit tests (T002, T009) | T002, T009 | Mock Communicate.stream() |
| Mock FFmpeg | Unit tests (T003, T006) | T003, T006 | Mock subprocess.run |
| Voiceover timing fixture | `test_subtitle.py`, `test_material_match.py` | T004, T005 | JSON fixture matching voiceover output |

## Parallel Groups

```
Group A: T001 ─────────────────────────────────────────────────┐
                                                                │
Group B: T002 ──────┐                                          │
        T003 ──────┤ (after T001)                              │
        T008* ─────┘                                           │
                                                                │
Group C: T004 ──────┐ (after T002)                             │
        T005 ──────┘                                           │
                                                                │
Group D: T006 ────────────── (after T002-T005)                 │
                                                                │
Group E: T007 ────────────── (after T006)                      │
                                                                │
Group F: T008 ────────────── (after T007)                      │
                                                                │
Group G: T009 ────────────── (after T007, T008)                │
                                                                │
                                                                │
*= T008 initially listed in Group B but web changes need T007  │
   API endpoint. Adjusted dependency to T007 only.              │
└───────────────────────────────────────────────────────────────┘
```

## Constitution Compliance Notes

| Principle | Task Coverage |
|-----------|--------------|
| P1: Evidence-First | Every task has test mapping; T009 provides E2E evidence |
| P2: User-Visible Slice | US-002 (T008) ensures video is visible on web; not just backend |
| P3: Simplicity | No Whisper (D007), no async queue, no scene detection (D008) |
| P4: Existing Architecture | All tasks follow STEP_SKILLS + _run_* pattern (T002-T007) |
| P5: Boundary Validation | T009 E2E test covers API + file serving + pipeline completion |
| P6: Workflow Over Editor | Linear 9-step pipeline (T007); no editing UI |
| P7: Reviewable Automation | Each media step writes artifacts (T002-T006) |
| P8: Rights-Aware | Existing disclaimer preserved; no auto-search |
| P9: Artifact-First | New ArtifactTypes (T001); every step writes typed artifacts |
