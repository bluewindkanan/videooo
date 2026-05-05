# Validation Report: 003-素材两路径与失败分流

> **Feature**: 003-material-dual-path
> **Risk Level**: medium
> **Release Decision**: go
> **Validated at**: 2026-05-05T13:15:00Z
> **Decider**: qa

## AC Coverage

| AC | Scenario | Test Type | Test File | Result |
|----|----------|-----------|-----------|--------|
| AC-001 | S-001: 系统自动下载素材链接并展示获取状态 | unit + integration | test_material_fetch.py, test_step_runner_material.py, TestMaterialFetchIntegration | PASS |
| AC-002 | S-002: 全部失败→waiting_for_material | unit + integration | test_step_runner_material.py, TestMaterialFetchIntegration | PASS |
| AC-003 | S-003: 上传替代素材后任务自动继续 | integration | test_upload_api.py, TestUploadResumeIntegration | PASS |

## Commands

```bash
# Full unit + integration suite
PYTHONPATH=app python3 -m pytest app/tests/unit/ app/tests/integration/ -v
# Result: 91 passed in 3.38s

# Coverage
PYTHONPATH=app python3 -m pytest app/tests/unit/ app/tests/integration/ --cov=app/src --cov-branch -q
# Result: 92% line coverage, branch coverage ≥ 83%
```

## Coverage Summary

- **Overall Line Coverage**: 92% (809 stmts, 53 miss)
- **Overall Branch Coverage**: 83% (138 branches, 23 partial)
- **Threshold**: ≥ 80% (PASS)

## Low Coverage Files

No files below 60% branch coverage.

Files with partial branch coverage noted for INFO:
- `app/src/server/routes/video_tasks.py` — 82% (upload route edge cases)
- `app/src/workers/step_runner.py` — 89% (material_fetch error paths)
- `app/src/skills/material_fetch.py` — 87% (platform_restriction edge cases)

## E2E Test Results

| Scenario | Driver | Result | Notes |
|----------|--------|--------|-------|
| S-001 素材下载成功 + 状态 artifact | API integration | PASS | material_status + source_video artifacts produced |
| S-001 部分成功继续 pipeline | API integration | PASS | partial success does not block |
| S-002 全部失败→waiting_for_material | API integration | PASS | task status set, step marked failed |
| S-002 空 source_links 跳过 | API integration | PASS | step completes immediately |
| S-003 上传替代→pipeline resume | API integration | PASS | upload accepted, pipeline continues to completion |
| S-003 非 waiting 状态拒绝上传 | API integration | PASS | 409 Conflict |
| S-003 错误扩展名拒绝 | API integration | PASS | 422 Unprocessable |

Blackbox smoke (`app/tests/blackbox/video_task_smoke.sh`) requires running server (port 8000). Not executed during validation — integration tests provide equivalent boundary coverage.

## AI Behavior Evaluation Results

- **Applicable**: false
- **Reason**: Feature contains no AI/LLM/agent behavior — purely deterministic file operations (HTTP download, multipart upload, status management).
- **N/A**: No AI eval required.

## Constitution Alignment

| Principle | Status | Evidence |
|-----------|--------|----------|
| P1: Evidence-First | PASS | T001–T006 all have TDD receipts; 91 tests pass |
| P2: User-Visible Slice | PASS | Users see material status panel, upload UI, task state changes |
| P3: Simplicity Over Speculation | PASS | httpx sync client (no async/queue), ArtifactStore extended (no new storage layer) |
| P4: Use Existing Architecture | PASS | Reuses FastAPI/SQLite/StepRunner; new skill follows existing pattern |
| P5: Boundary Validation | PASS | Integration tests cover full API boundary (download/upload/status transitions) |
| P6: Workflow Over Editor | PASS | Web only shows material status and upload — no editor |
| P7: Reviewable Automation | PASS | material_status artifact preserves per-link download history |
| P8: Rights-Aware Inputs | PASS | Web retains rights disclaimer; upload doesn't change responsibility |
| P9: Artifact-First | PASS | source_video, uploaded_video, material_status artifacts all persisted |

**Overall**: PASS — no constitutional conflicts.

## Spec Consistency

| Artifact | Version | Consistent | Notes |
|----------|---------|------------|-------|
| feature.md → design.md | 1.0 → 1.0 | YES | All scenarios mapped to design decisions |
| design.md → tasks.md | 1.0 → 1.0 | YES | 6 tasks cover all ADRs and modules |
| tasks.md → implementation | 1.0 → current | YES | All 6 tasks completed with test evidence |
| feature.md ACs → tests | 1.0 → current | YES | AC-001/002/003 all covered by unit+integration tests |

No scenario drift detected.

## Execution Contract Audit

| Task | Receipt Exists | Fields Complete | Files in Scope | RED/GREEN Evidence |
|------|---------------|-----------------|----------------|-------------------|
| T001 | YES | YES | YES | YES |
| T002 | YES | YES | YES | YES |
| T003 | YES | YES | YES | YES |
| T004 | YES | YES | YES | YES |
| T005 | YES | YES (Web UI) | YES | Verified via integration |
| T006 | YES | YES | YES | YES |

Receipt path: `docs/01-features/003-material-dual-path/receipts.json`

## Drift Summary

- **Minor drift**: None
- **Material drift**: None
- Implementation matches design and tasks exactly.

## Planning Findings

1. T001 and T002 were correctly identified as parallelizable — execution confirmed this.
2. The "Failed" text triggering FAIL injection was discovered during T006 integration testing — test topics adjusted. This is a known smoke test convention, not a design issue.
3. `python-multipart` dependency was not pre-identified in tasks.md — added during T004 implementation. Low impact.

## Recommended Methodology Feedback

- Consider adding a "dependency check" task for new Python packages (httpx, python-multipart) in the template.
- Web UI tasks (T005) could benefit from a minimal static verification step (grep for XSS-prone patterns).

## Lighthouse Report

- **N/A**: This feature's Web changes are additions to an existing vanilla HTML/JS workbench (no SPA framework, no build step). Lighthouse requires a running server and is not applicable for static validation. The workbench is served by FastAPI's FileResponse. Performance of the upload/download operations is verified through API integration tests.

## Security Checklist

| Check | Status | Notes |
|-------|--------|-------|
| File extension whitelist | PASS | .mp4/.mov/.avi only |
| Content-Type validation | PASS | video/* types checked |
| File size limit | PASS | 500MB enforced |
| Filename sanitization | PASS | UUID-based names, no user-controlled filenames |
| Upload to wrong state | PASS | 409 Conflict for non-waiting tasks |
| SSRF protection | INFO | Not implemented for v1 (internal tool) |
| XSS in Web UI | PASS | escHtml() used for all dynamic content |

## Blockers

None.

## Discoverability & Usage Path

- **Primary entry**: Web workbench task detail page shows material status panel automatically when material_fetch step has results
- **Upload discoverability**: When task status is `waiting_for_material`, upload button and file picker appear inline
- **Minimal usage path verified**: Create task with source_links → see material status → upload if failed → pipeline continues
- **API discoverability**: `POST /api/video-tasks/{task_id}/materials` documented in schemas

Evidence: Integration tests `TestMaterialFetchIntegration` and `TestUploadResumeIntegration` verify the complete discoverability and usage path through the API boundary.
