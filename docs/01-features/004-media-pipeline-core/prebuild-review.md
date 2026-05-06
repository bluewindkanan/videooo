---
feature_id: "004"
review_type: prebuild
created_at: 2026-05-05
---

# Pre-Build Review: 004-media-pipeline-core

## Spec Convergence

| Dimension | feature.md | design.md | tasks.md | Aligned? |
|-----------|-----------|-----------|----------|----------|
| US-001: 自动生成视频初稿 | 5 scenarios (S-001~S-005) | 5 skill designs (voiceover→compose) | T002-T006 | Yes |
| US-002: Web 预览下载 | S-006 | Web video preview + download endpoint | T008 | Yes |
| 管线编排 | FR-010, FR-011 | Pipeline orchestration section | T007 | Yes |
| 素材降级 | FR-012 | D010 solid color fallback | T006 (fallback logic) | Yes |
| 错误处理 | FR-020~FR-022 | Error handling per skill | T002-T007 | Yes |
| 性能 | SC-PERF-001, SC-PERF-002 | Sync pipeline accepted | T009 (E2E timing) | Yes |
| 质量标准 | SC-QUAL-001~003 | E2E Test Strategy | T009 | Yes |
| AI behavior eval | applicable=false | N/A section | Not required | Yes |
| Entry points | Section 7.1 | Entry Points / Discovery Path | T008 (web), T007 (API) | Yes |
| Non-goals | 封面/BGM/转场/异步 | Not in design | Not in tasks | Yes |

## Coverage Matrix

| Scenario | AC | Design Section | Task | Test Type | Gap? |
|----------|----|---------------|----|-----------|------|
| S-001 | AC-001 | voiceover skill | T002 | unit + E2E (T009) | No |
| S-002 | AC-002 | material_extract skill | T003 | unit + E2E (T009) | No |
| S-003 | AC-003 | material_match skill | T004 | unit + E2E (T009) | No |
| S-004 | AC-004 | subtitle skill | T005 | unit + E2E (T009) | No |
| S-005 | AC-005 | video_compose skill | T006 | unit + E2E (T009) | No |
| S-006 | AC-006 | Web preview + API file endpoint | T007+T008 | smoke + E2E (T009) | No |

## Gate Checks

### intent_review
- required: true
- status: confirmed
- confirmed_by: user
- confirmed_at: 2026-05-05 21:50 CST
- **Result**: PASS

### split_assessment
- triggered_conditions: none
- decision: proceed
- **Result**: PASS

### experience_surface (user_visible)
- Discoverability: Video player appears only when final_video artifact exists (design.md Entry Points)
- Minimal usage path: Submit task → wait for pipeline → play/download video (design.md + T008)
- **Result**: PASS

### ai_behavior_eval
- applicable: false
- required: false
- **Result**: PASS (not required)

### Constitution compliance
- All 9 principles covered in tasks.md Constitution Compliance Notes
- No conflicts identified
- **Result**: PASS

### Story completeness
- US-001: 5 scenarios → 5 skill tasks (T002-T006) + E2E (T009)
- US-002: 1 scenario → API (T007) + Web (T008) + E2E (T009)
- **Result**: PASS

### Underbuild/overbuild check
- Underbuild risk: None — all scenarios have design + task + test
- Overbuild risk: None — no tasks outside feature scope; non-goals (封面/BGM/转场/异步) not included
- **Result**: PASS

### Regression coverage (extension mode)
- Reuse analysis: documented in tasks.md
- Callsite inventory: documented in tasks.md
- All existing tests must pass after each task
- T007 (pipeline orchestration) is highest regression risk
- **Result**: PASS

## Feature Review Concerns Resolution

| Concern (from feature_review_gate) | Resolution in Design/Tasks |
|-----------------------------------|---------------------------|
| FFmpeg 环境依赖 | D009 + T002 ffmpeg_utils.check_ffmpeg_available() |
| 同步管线耗时提示 | Web auto-refresh 5s + step cards show status |
| 素材不足降级方案 | D010 solid color fallback + T006 fallback mode |
| voiceover timing 精度 | D006 word boundary timing + D007 direct SRT generation |

## Prebuild Review Gate

- **Status**: passed
- **Blockers**: none
- **Concerns**:
  - FFmpeg must be available for E2E tests; skip logic required for CI environments without FFmpeg
  - edge-tts external API dependency; unit tests must mock it
- **Recommended next action**: `/bewater-build`
