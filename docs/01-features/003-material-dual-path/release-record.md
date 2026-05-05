# Release Record: 003-素材两路径与失败分流

> **Feature**: 003-material-dual-path
> **Released at**: 2026-05-05T13:30:00Z
> **Release Boundary**: local
> **Release Decision**: go

## Ship Precheck Gate

- **Status**: go
- **Evidence Checked**: true
- **Validation Outcome**: ready_for_precheck / go
- **All Gates**: feature_review=passed, architect=passed, tasks=passed, prebuild_review=passed, foundation=passed

## Adapter Results

| Adapter | Type | Actions | Status |
|---------|------|---------|--------|
| local-record | local | release_record, commit | passed |

## Evidence

- Validation Report: `docs/01-features/003-material-dual-path/validation-report.md`
- TDD Receipts: `docs/01-features/003-material-dual-path/receipts.json`
- Test Suite: 91 passed, 92% line coverage, 83% branch coverage
- AC Coverage: AC-001 PASS, AC-002 PASS, AC-003 PASS
- Spec Consistency: No drift detected
- Security Checklist: All PASS
- Constitution Alignment: All 9 principles PASS

## Implementation Summary

- **T001**: MaterialFetchSkill — httpx-based URL download with streaming write
- **T002**: ArtifactStore extension — source_video/material_status artifact types
- **T003**: SQLite schema + VideoTask model — waiting_for_material state, material_status field
- **T004**: Upload API — POST /api/video-tasks/{task_id}/materials with file validation
- **T005**: Web workbench — material status panel, upload UI, rights disclaimer
- **T006**: StepRunner integration — material_fetch step, failure→waiting_for_material, upload→resume

## Post-Release Notes

- SSRF protection deferred to v1 (internal tool scope)
- Blackbox smoke test requires running server, covered by integration tests
- python-multipart dependency added during T004 (not pre-identified in tasks.md)
