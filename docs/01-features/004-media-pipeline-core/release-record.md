---
feature_id: "004"
release_type: local
released_at: 2026-05-05
ship_precheck_gate: go
release_decision: go
---

# Release Record: 004-media-pipeline-core

## Release Summary

**Feature**: 媒体管线核心（配音 + 素材处理 + 字幕 + 合成）
**Scope**: 5 个新 media skills + pipeline orchestration + web video preview
**Test Evidence**: 181 passed, 0 failed, 2 skipped (FFmpeg libass env)
**Release Boundary**: local

## Shipped Stories

| Story | Description | Scenarios |
|-------|-------------|-----------|
| US-001 | 自动生成视频初稿 | S-001~S-005 |
| US-002 | Web 工作台预览和下载视频 | S-006 |

## New Files

| File | Purpose |
|------|---------|
| app/src/skills/voiceover.py | TTS 配音生成（edge-tts） |
| app/src/skills/material_extract.py | 素材切片（FFmpeg） |
| app/src/skills/material_match.py | 配音-素材匹配 |
| app/src/skills/subtitle.py | SRT 字幕生成 |
| app/src/skills/video_compose.py | 视频合成（FFmpeg） |
| app/src/media/ffmpeg_utils.py | FFmpeg 工具模块 |
| app/tests/fixtures/test_video.mp4 | 测试视频素材 |

## Modified Files

| File | Change |
|------|--------|
| app/src/domain/models.py | +4 ArtifactType enum values |
| app/src/artifacts/store.py | Extended for .mp3/.srt |
| app/src/workers/step_runner.py | +5 skill registrations + _run_* methods |
| app/src/server/routes/video_tasks.py | 9-step pipeline + file serving endpoint |
| app/src/web/workbench.html | Video player CSS |
| app/src/web/workbench.js | Video preview + download rendering |

## Dependencies Added

- edge-tts>=6.1.0

## Gate Evidence

| Gate | Status | Evidence |
|------|--------|----------|
| feature_review_gate | passed | feature-review.md |
| tasks_gate | passed | tasks.md (9 tasks, all done) |
| prebuild_review_gate | passed | prebuild-review.md |
| review_gate | passed | review-note.md |
| ship_precheck_gate | go | validation-report.md |
