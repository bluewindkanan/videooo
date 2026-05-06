---
feature_id: "004"
design_for: 媒体管线核心（配音 + 素材处理 + 字幕 + 合成）
created_at: 2026-05-05
complexity_tier: deep
implementation_mode: extension
experience_surface: user_visible
---

# Design: 004-media-pipeline-core

## Overview

补完"输入主题 → 输出视频"的 MVP 闭环。在现有 LLM 编导管线（review_script 之后）接入 5 个媒体处理步骤：voiceover → material_extract → material_match → subtitle → video_compose。新增 Web 视频预览和下载能力。

**前置条件**：Feature 002 LLM 管线 + Feature 003 素材双路径已交付。

**核心架构约束**：所有新 skill 遵循现有 `STEP_SKILLS` 注册 + `_run_*` 方法模式；管线保持同步执行。

---

## Architecture Decisions

### D006: Per-segment TTS with edge-tts word boundary timing

- **Choice**: 为每个 storyboard segment 独立生成 TTS 音频，捕获 word boundary 事件
- **Reason**: 分段生成提供精确的 segment 时长（用于素材匹配）和 word-level 时间戳（用于字幕生成），且支持单段重试
- **Alternative**: 整段生成 + Whisper ASR — 引入额外依赖和转录误差，文案已知时无必要
- **Consequence**: edge-tts 是 async API，skill 内部用 `asyncio.run()` 包装；需引入 edge-tts 依赖
- **Voice**: 默认 `zh-CN-XiaoxiaoNeural`，可通过 `VIDEOOO_TTS_VOICE` 环境变量切换

### D007: edge-tts timing for subtitles (no Whisper)

- **Choice**: 使用 edge-tts word boundary timing 直接生成 SRT 字幕
- **Reason**: 文案已知、TTS 引擎提供精确时间戳，比 ASR 转录更准确；减少 faster-whisper 依赖
- **Consequence**: 字幕质量与 TTS timing 精度绑定；若 edge-tts 不提供 timing 则需 fallback 到按 segment 切分
- **faster-whisper**: 不引入，避免增加依赖复杂度。若后续需要 ASR 能力可在 PC-006 引入

### D008: Fixed-duration clip extraction + sequential duration-based matching

- **Choice**: 将源视频切成固定时长片段（~5s），然后按 voiceover segment 时长顺序分配
- **Reason**: 简单、可预测、不依赖源视频内容分析
- **Alternative**: 基于场景检测的智能切片 — 过度设计，首版不需要
- **Consequence**: 匹配精度一般，但对知识分享类视频可接受；素材不足时循环使用

### D009: FFmpeg concat demuxer for video composition

- **Choice**: 使用 FFmpeg concat demuxer + inpoint/outpoint 拼接片段，叠加音频和字幕
- **Reason**: 单一 FFmpeg 命令完成合成，无需中间步骤；与架构约束中"服务端 FFmpeg"一致
- **Consequence**: 需要 FFmpeg 运行时环境；长视频合成耗时可观（首版可接受 30-60s）

### D010: No source videos → solid color fallback

- **Choice**: 当无源视频时，生成纯色背景 + 配音 + 字幕的 MP4
- **Reason**: 保证管线始终产出可播放视频，不因素材缺失而完全失败
- **Consequence**: 视觉效果差，但满足"可预览可评估"的 MVP 目标

---

## Story Inventory

| Story | Priority | Scenarios | Tech Skills |
|-------|----------|-----------|-------------|
| US-001: 自动生成视频初稿 | P1 | S-001, S-002, S-003, S-004, S-005 | voiceover, material_extract, material_match, subtitle, video_compose |
| US-002: Web 工作台预览和下载 | P1 | S-006 | web video player + download endpoint |

## Scenario Coverage

| Scenario | Story | Covered By | Test Level |
|----------|-------|-----------|------------|
| S-001: 生成配音音频 | US-001 | voiceover skill unit + integration | Unit + API |
| S-002: 切出素材片段 | US-001 | material_extract skill unit | Unit + API |
| S-003: 配音匹配素材 | US-001 | material_match skill unit | Unit |
| S-004: 生成字幕 | US-001 | subtitle skill unit | Unit |
| S-005: 合成最终视频 | US-001 | video_compose skill + E2E | Unit + E2E |
| S-006: Web 预览下载 | US-002 | web UI + API endpoint | E2E (smoke) |

---

## Per-Story Technical Approach

### US-001 — voiceover skill

**File**: `app/src/skills/voiceover.py` (new)

**Input**:
- `storyboard_segments: list[dict]` — from storyboard step's parsed_json artifact
- `artifact_store: ArtifactStore` — for writing audio files
- `task_id: str`

**Logic**:
1. For each storyboard segment, extract `voiceover_text`
2. Use edge-tts `Communicate.stream()` to generate audio + capture `WordBoundary` events
3. Write per-segment MP3 files via `artifact_store.write_file(task_id, "voiceover", "audio", ...)`
4. Concatenate all segment audios into full voiceover using FFmpeg concat demuxer
5. Compute timing data: per-segment duration (from FFmpeg probe or edge-tts offset), word boundaries with absolute offsets

**Output**: `dict` — timing_data
```json
{
  "segments": [
    {
      "segment_index": 0,
      "voiceover_text": "...",
      "segment_audio_ref": "path/to/seg0.mp3",
      "duration_seconds": 5.23,
      "word_boundaries": [
        {"text": "word", "offset_ms": 0, "duration_ms": 200}
      ]
    }
  ],
  "total_duration_seconds": 30.5,
  "full_audio_ref": "path/to/full.mp3"
}
```

**Error handling**:
- edge-tts API error → raise `VoiceoverError` with segment info
- Empty storyboard → raise `VoiceoverError("no_segments")`

**StepRunner `_run_voiceover`**:
1. Read storyboard parsed_json artifact
2. Call `run_voiceover()`
3. Write timing_data as parsed_json artifact (ArtifactType.parsed_json)
4. Register segment audio + full audio as ArtifactType.audio artifacts

---

### US-001 — material_extract skill

**File**: `app/src/skills/material_extract.py` (new)

**Input**:
- `source_video_refs: list[str]` — storage_ref paths from source_video artifacts
- `artifact_store: ArtifactStore`
- `task_id: str`

**Logic**:
1. If no source_video_refs → return empty clip_manifest
2. For each source video:
   a. Probe duration via `ffprobe`
   b. Cut into fixed-duration clips (~5s each) using `ffmpeg -ss START -to END -c copy`
   c. Write clip files via artifact_store
3. Build clip_manifest with per-clip metadata

**Output**: `dict` — clip_manifest
```json
{
  "clips": [
    {
      "clip_index": 0,
      "source_ref": "path/to/source.mp4",
      "start_seconds": 0,
      "end_seconds": 5.0,
      "duration_seconds": 5.0,
      "storage_ref": "path/to/clip0.mp4"
    }
  ],
  "total_clip_duration_seconds": 25.0
}
```

**FFmpeg commands**:
```bash
# Probe duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 source.mp4

# Extract clip
ffmpeg -i source.mp4 -ss START -to END -c copy -avoid_negative_ts make_zero clip_N.mp4
```

**Error handling**:
- FFmpeg not found → raise with installation instructions
- ffprobe fails → skip source video, log warning
- Clip extraction fails → skip that clip, continue with others

**StepRunner `_run_material_extract`**:
1. Read source_video artifact refs from material_fetch step
2. Call `run_material_extract()`
3. Write clip files (already written by skill)
4. Write clip_manifest as parsed_json artifact
5. Register clip files as ArtifactType.clip artifacts

---

### US-001 — material_match skill

**File**: `app/src/skills/material_match.py` (new)

**Input**:
- `voiceover_timing: dict` — timing_data from voiceover step
- `clip_manifest: dict` — from material_extract step

**Logic**:
1. Build flat clip pool from clip_manifest
2. If pool empty → return matches with no assigned_clips (triggers fallback)
3. For each voiceover segment (sorted by segment_index):
   - Track cumulative clip position
   - Assign clips sequentially to cover segment duration
   - If clips exhausted → loop back to clip 0
4. Record per-segment assignment with clip indices and time offsets

**Output**: `dict` — matched_segments
```json
{
  "matches": [
    {
      "segment_index": 0,
      "voiceover_duration": 5.23,
      "assigned_clips": [
        {"clip_index": 0, "start_seconds": 0.0, "end_seconds": 5.0, "duration_used": 5.0},
        {"clip_index": 1, "start_seconds": 0.0, "end_seconds": 0.23, "duration_used": 0.23}
      ]
    }
  ],
  "fallback_mode": false
}
```

**No external dependencies** — pure Python computation.

**StepRunner `_run_material_match`**:
1. Read voiceover_timing (parsed_json from voiceover)
2. Read clip_manifest (parsed_json from material_extract)
3. Call `run_material_match()`
4. Write matched_segments as parsed_json artifact (ArtifactType.parsed_json)

---

### US-001 — subtitle skill

**File**: `app/src/skills/subtitle.py` (new)

**Input**:
- `voiceover_timing: dict` — timing_data from voiceover step
- `artifact_store: ArtifactStore`
- `task_id: str`

**Logic**:
1. Read word_boundaries from voiceover_timing segments
2. For each segment, create one SRT entry:
   - Start time = segment's first word offset
   - End time = segment's last word offset + duration
   - Text = segment voiceover_text (full sentence)
3. If segment > 10s, split at mid-sentence word boundary into multiple entries
4. Format as SRT with millisecond precision
5. Write .srt file via artifact_store

**Output**: `dict` — subtitle_metadata
```json
{
  "entry_count": 5,
  "total_duration_seconds": 30.5,
  "source": "edge_tts_timing",
  "srt_ref": "path/to/subs.srt"
}
```

**SRT format**:
```
1
00:00:00,000 --> 00:00:05,230
Segment 1 voiceover text

2
00:00:05,230 --> 00:00:12,450
Segment 2 voiceover text
```

**Fallback**: If word_boundaries are empty, use segment start/end estimates from storyboard.

**StepRunner `_run_subtitle`**:
1. Read voiceover_timing (parsed_json from voiceover)
2. Call `run_subtitle()`
3. Write .srt file (already written by skill)
4. Write subtitle_metadata as parsed_json artifact
5. Register .srt file as ArtifactType.subtitle artifact

---

### US-001 — video_compose skill

**File**: `app/src/skills/video_compose.py` (new)

**Input**:
- `matched_segments: dict` — from material_match step
- `voiceover_timing: dict` — from voiceover step (for full_audio_ref and total_duration)
- `subtitle_ref: str` — path to .srt file
- `clip_manifest: dict` — for clip file paths
- `artifact_store: ArtifactStore`
- `task_id: str`

**Logic — Normal mode (clips available)**:
1. Build FFmpeg concat input file from matched_segments:
   ```
   file 'clip0.mp4'
   inpoint 0.0
   outpoint 5.0
   file 'clip1.mp4'
   inpoint 0.0
   outpoint 0.23
   ...
   ```
2. Run FFmpeg: concat clips + voiceover audio + burn subtitles
   ```bash
   ffmpeg -f concat -safe 0 -i concat.txt \
     -i voiceover.mp3 \
     -vf "subtitles=subs.srt:force_style='FontSize=22,PrimaryColour=&Hffffff,FontName=PingFang SC'" \
     -c:v libx264 -c:a aac -pix_fmt yuv420p \
     -map 0:v -map 1:a -shortest \
     output.mp4
   ```

**Logic — Fallback mode (no clips)**:
1. Generate solid color background video for total duration:
   ```bash
   ffmpeg -f lavfi -i "color=c=0x1a1a2e:s=1280x720:d=DURATION:r=30" \
     -i voiceover.mp3 \
     -vf "subtitles=subs.srt:force_style='FontSize=22,PrimaryColour=&Hffffff,FontName=PingFang SC'" \
     -c:v libx264 -c:a aac -pix_fmt yuv420p \
     -shortest output.mp4
   ```

**Output**: `dict` — compose_log
```json
{
  "duration_seconds": 30.5,
  "resolution": "1280x720",
  "has_visual": true,
  "has_audio": true,
  "has_subtitles": true,
  "fallback_mode": false,
  "storage_ref": "path/to/output.mp4"
}
```

**Error handling**:
- FFmpeg not found → fail fast
- Composition fails → preserve intermediate artifacts, raise with FFmpeg stderr

**StepRunner `_run_video_compose`**:
1. Read matched_segments, voiceover_timing, subtitle_ref, clip_manifest
2. Call `run_video_compose()`
3. Register output.mp4 as ArtifactType.final_video artifact
4. Write compose_log as parsed_json artifact

---

### US-002 — Web video preview and download

**New API endpoint**: `GET /api/video-tasks/{task_id}/artifacts/{artifact_id}/file`

Returns binary file with proper Content-Type for streaming. Uses FastAPI's `FileResponse`.

**Workbench changes** (workbench.html + workbench.js):

1. In `renderProductSections()`: detect `final_video` artifact type
2. Render `<video controls>` tag pointing to `/file` endpoint
3. Render download link `<a href="..." download>`
4. Only show when final_video artifact exists (same pattern as script/storyboard sections)

**Artifact content API update**: In `get_artifact_content`, add `.mp3` and `.srt` to non-binary handling or binary metadata:
- `.mp3`: return metadata (binary_file note)
- `.srt`: return text content (add to readable extensions)

---

## Shared Cross-Story Concerns

### ArtifactType Extension

Add to `ArtifactType` enum in `models.py`:
```
audio = "audio"
clip = "clip"
subtitle = "subtitle"
final_video = "final_video"
```

### ArtifactStore Extension

In `store.py`:
- Extend `ALLOWED_EXTENSIONS`: add `.mp3`, `.wav`, `.srt`
- Extend `_VIDEO_EXTENSIONS` → `_MEDIA_EXTENSIONS`: add `.mp3`, `.srt` for listing

### Pipeline Orchestration

`DEFAULT_STEP_KEYS` in `video_tasks.py`:
```python
DEFAULT_STEP_KEYS = [
    "material_fetch", "script_generation", "storyboard", "review_script",
    "voiceover", "material_extract", "material_match", "subtitle", "video_compose"
]
```

Pipeline execution in `create_video_task`:
```python
# After material_fetch
if task.status != TaskStatus.waiting_for_material:
    for step_key in DEFAULT_STEP_KEYS[1:]:  # all steps after material_fetch
        runner.run_step(task_id=task.id, step_key=step_key)
```

Same pattern in `upload_material` resume: run all remaining steps.

### FFmpeg Dependency

Add `app/src/media/ffmpeg_utils.py` with:
- `check_ffmpeg_available() -> tuple[bool, str]` — check at step entry
- `probe_duration(path) -> float` — get media file duration
- `run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess` — unified FFmpeg runner with error handling

### New Dependencies

```
edge-tts>=6.1.0
```

No faster-whisper (D007 decision).

### Error Handling Pattern

Each media skill raises typed exceptions:
- `FFmpegNotFoundError` — FFmpeg not installed
- `FFmpegError` — FFmpeg command failed (includes stderr)
- `VoiceoverError` — TTS generation failed

StepRunner catches these and calls `set_step_failed()` with appropriate error_category:
- `non_retryable` for FFmpegNotFoundError
- `retryable` for transient failures
- `needs_user_action` for material-related issues

---

## Artifact Schemas & Data Flow

### Step Dependency Graph

```
review_script (existing)
    ↓
voiceover ─────────────────────→ subtitle
    ↓                              ↓
material_extract → material_match → video_compose
                                       ↑
                              subtitle ┘
```

### Step Input/Output Summary

| Step | Reads From | Writes |
|------|-----------|--------|
| voiceover | storyboard parsed_json | audio files (per-segment + full), timing_data parsed_json |
| material_extract | source_video artifacts (storage_refs) | clip files, clip_manifest parsed_json |
| material_match | voiceover timing_data, material_extract clip_manifest | matched_segments parsed_json |
| subtitle | voiceover timing_data | .srt file, subtitle_metadata parsed_json |
| video_compose | matched_segments, voiceover_timing (full_audio_ref), subtitle .srt, clip files | final_video .mp4, compose_log parsed_json |

---

## E2E Test Strategy

### Driver
- **Primary**: FastAPI `TestClient` for API-level E2E
- **Web smoke**: Manual or Playwright (not required for first slice, but the API test must prove the video is downloadable)

### Scenario Coverage
1. **Full pipeline E2E**: Submit task with topic + small test video URL → verify final_video artifact exists and is a valid MP4
2. **No source videos**: Submit task with no source links → verify final_video artifact exists (fallback mode)
3. **Video preview API**: After pipeline completes, GET artifact file endpoint returns video with correct Content-Type
4. **Step retry**: Fail a step (e.g., inject FFmpeg error), retry, verify completion

### Test Assets
- `app/tests/fixtures/test_video.mp4` — short (3-5s) test video file
- Test uses mocked TTS (no real edge-tts calls in CI) or short text for fast execution

### Data/Auth Setup
- None required (no auth in current system)

### Artifact Policy
- E2E test verifies: each step produces at least one artifact, final_video is non-zero bytes, compose_log has `has_visual` and `has_audio` flags

### Test Isolation
- Unit tests: mock FFmpeg subprocess, mock edge-tts
- Integration tests: use real FFmpeg if available, skip if not (`pytest.mark.skipif`)
- E2E: mock TTS, use real FFmpeg with test fixtures

---

## Constitution Notes

| Principle | Impact | Design Compliance |
|-----------|--------|-------------------|
| P1: Evidence-First | Each skill has unit tests; E2E test covers full pipeline | TDD per skill, integration test with real FFmpeg |
| P2: User-Visible Slice | Final output is a playable, downloadable video | US-002 ensures Web visibility |
| P3: Simplicity Over Speculation | No Whisper ASR, no async queue, no scene detection | Use edge-tts timing directly; sync pipeline; fixed-duration clips |
| P4: Use Existing Architecture | New skills follow STEP_SKILLS + _run_* pattern | All 5 skills use same registration pattern |
| P5: Boundary Validation | API-level E2E + FFmpeg smoke tests | TestClient + real FFmpeg composition |
| P6: Workflow Over Editor | Linear pipeline, no editing UI | 9-step linear pipeline |
| P7: Reviewable Automation | Every step writes artifacts; intermediate files preserved | Audio, clips, subtitles, compose log all persisted |
| P8: Rights-Aware Inputs | No change — user responsible for source material | Existing disclaimer preserved |
| P9: Artifact-First | Each step writes typed artifacts before completing | New ArtifactTypes for audio, clip, subtitle, final_video |

---

## AI Behavior Evaluation Strategy

- `applicable`: false
- `reason`: Feature contains TTS (edge-tts deterministic generation) and FFmpeg media processing. No LLM/Agent behavior. Subtitle generation uses TTS timing, not semantic judgment.
- No eval scenarios, dataset, scorer, or threshold required.

---

## Entry Points / Discovery Path

### Primary entry point
Web 工作台任务详情页 — 当 `video_compose` 步骤完成时，自动出现视频播放器和下载按钮。

### Secondary entry point
API `GET /api/video-tasks/{id}/artifacts` — 返回 final_video artifact 元信息
API `GET /api/video-tasks/{id}/artifacts/{artifact_id}/file` — 流式返回视频文件

### Discovery behavior
- 视频预览区域仅在 final_video artifact 存在时显示
- 步骤卡片显示每个媒体处理步骤的状态（running/completed/failed）
- 失败步骤显示重试按钮

### Minimal usage path
创建任务（输入主题 + 素材链接）→ 等待管线完成（自动轮询）→ 任务详情页 → 播放/下载视频

---

## Risks

### Risk 1: FFmpeg environment differences
- **Severity**: High | **Likelihood**: Medium
- **Mitigation**: check_ffmpeg_available() at step entry; clear error message with install instructions
- **Monitoring**: E2E test skipped when FFmpeg unavailable

### Risk 2: edge-tts API instability or rate limiting
- **Severity**: Medium | **Likelihood**: Low
- **Mitigation**: Voice adapter isolation; can swap to local TTS or other providers
- **Monitoring**: VoiceoverError caught and retryable

### Risk 3: Clip duration < voiceover duration
- **Severity**: Low | **Likelihood**: Medium
- **Mitigation**: Clip looping in material_match; fallback to solid color if looping insufficient
- **Monitoring**: compose_log.fallback_mode flag

### Risk 4: Synchronous pipeline timeout (30-60s total)
- **Severity**: Medium | **Likelihood**: High (expected behavior)
- **Mitigation**: First version acceptable; Web auto-refresh every 5s shows progress
- **Monitoring**: User feedback; can add async queue later

### Risk 5: Chinese font not available for subtitle burn-in
- **Severity**: Low | **Likelihood**: Low (macOS has PingFang SC; Linux may need fonts-noto-cjk)
- **Mitigation**: Test with default font; document font requirement
- **Monitoring**: Visual inspection of burned subtitles
