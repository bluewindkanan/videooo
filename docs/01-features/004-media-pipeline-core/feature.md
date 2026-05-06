---
feature_id: "004"
feature_name: 媒体管线核心（配音 + 素材处理 + 字幕 + 合成）
created_at: 2026-05-05
created_by: /bewater-goal
status: specified
lifecycle_status: active
last_verified_commit: null
last_verified_at: null
implementation_paths:
  - app/src/skills/voiceover.py — 新建 TTS 配音 skill
  - app/src/skills/material_extract.py — 新建素材切片 skill
  - app/src/skills/material_match.py — 新建片段匹配 skill
  - app/src/skills/subtitle.py — 新建字幕生成 skill
  - app/src/skills/video_compose.py — 新建视频合成 skill
  - app/src/workers/step_runner.py — 注册 5 个新 skill + _run_* 方法
  - app/src/server/routes/video_tasks.py — DEFAULT_STEP_KEYS 扩展 + 管线编排
  - app/src/domain/models.py — ArtifactType 新增 audio/subtitle/clip/final_video
  - app/src/web/workbench.html — 视频预览和下载 UI
  - app/src/web/workbench.js — 视频预览和下载交互
risk_level: high
complexity_tier: deep
implementation_mode: extension
experience_surface: user_visible
ai_behavior_eval:
  applicable: false
  required: false
  eval_level: none
  reason: Feature 包含 TTS（edge-tts 确定性生成）和 FFmpeg 媒体处理，无 LLM/Agent 行为。字幕生成使用 Whisper ASR 属于确定性转录，不涉及语义判断。
  primary_risks: []
  success_threshold: N/A — no AI behavior eval required
existing_implementation_note: Feature 002 已交付 LLM 编导管线（script_generation → storyboard → review_script），Feature 003 已交付素材双路径（material_fetch + upload）。当前 DEFAULT_STEP_KEYS = [material_fetch, script_generation, storyboard, review_script]。需要在 review_script 之后接入 5 个媒体处理步骤。无配音、切片、匹配、字幕、合成代码。StepRunner 已有 skill 注册和 _run_* 方法模式，新 skill 遵循相同模式。
rework_risk: high
rework_risk_factors:
  affects_payment_or_billing: false
  affects_auth_or_permissions: false
  affects_data_model_or_migration: true
  affects_public_api_or_contract: true
  rollback_difficulty: medium
  blast_radius: multi_module
intent_review:
  required: true
  status: confirmed
  confirmed_by: user
  confirmed_at: 2026-05-05 21:50 CST
  reviewed_items:
    - user_story
    - non_goals
    - key_scenarios
  notes: 用户已确认 5 步媒体管线 + Web 预览下载的 User Story、Non-goals（不做封面/成片审查/BGM/转场）、方案 B（同步自动流水线）。
split_assessment:
  user_value_points: 1
  scenarios_count: 6
  impacted_modules_count: 5
  unresolved_clarifications_count: 0
  complex_scenario_dependencies: false
  triggered_conditions: []
  decision: proceed
  override_by: null
  override_reason: N/A — no split conditions triggered
scenarios:
  - id: S-001
    story_id: US-001
    title: 系统为分镜生成配音音频
    given: storyboard 步骤已产出分镜表，每个分镜包含 voiceover_text
    when: 系统执行 voiceover 步骤
    then: 生成 audio artifact（MP3），包含完整的旁白配音，可播放
    acceptance_refs: AC-001
  - id: S-002
    story_id: US-001
    title: 系统从源视频中切出片段
    given: material_fetch 已下载源视频文件
    when: 系统执行 material_extract 步骤
    then: 从源视频切出多个片段（clip artifacts），每个片段有时长和起止时间
    acceptance_refs: AC-002
  - id: S-003
    story_id: US-001
    title: 系统将配音片段匹配到素材片段
    given: voiceover 和 material_extract 步骤已完成
    when: 系统执行 material_match 步骤
    then: 每个配音片段分配到对应的素材片段，匹配关系可查看
    acceptance_refs: AC-003
  - id: S-004
    story_id: US-001
    title: 系统生成字幕文件
    given: voiceover 步骤已生成配音音频
    when: 系统执行 subtitle 步骤
    then: 生成 SRT 字幕 artifact，时间轴与音频对齐
    acceptance_refs: AC-004
  - id: S-005
    story_id: US-001
    title: 系统合成最终视频
    given: material_match、voiceover 和 subtitle 步骤已完成
    when: 系统执行 video_compose 步骤
    then: 生成 final_video artifact（MP4），包含配音、画面和烧录字幕，可下载
    acceptance_refs: AC-005
  - id: S-006
    story_id: US-002
    title: 用户在 Web 工作台预览和下载视频
    given: video_compose 步骤已生成最终视频
    when: 用户在任务详情页查看
    then: 看到视频预览播放器和下载按钮，可播放和下载 MP4 文件
    acceptance_refs: AC-006
---

# 功能：媒体管线核心（配音 + 素材处理 + 字幕 + 合成）

> **用途**: 定义功能的目标和验收标准
>
> **LLM 行为约束**:
> - ✅ 只描述 WHAT（做什么）和 WHY（为什么做）
> - ❌ 不描述 HOW（怎么做）— 技术细节属于 design.md / tasks.md

## Product Decision Summary（产品决策摘要）

### Goal（用户结果）*

内容团队成员提交主题和素材链接后，系统能自动生成带配音、背景画面和字幕的完整知识分享短视频初稿（MP4），用户可在 Web 工作台预览和下载。

### Vision Link（服务愿景）*

- Vision section: Narrowest Wedge + Core Promise
- Link reason: 这个 feature 直接兑现 Vision 中"输入主题后得到可预览初稿"的核心承诺，是 PC-002 原始 success_definition 中"导出成片初稿"的补完。

### User Scenario（触发场景）*

内容团队成员已有通过 AI 编导生成的文案和分镜，需要把结构化产物变成真正可播放的视频初稿，用于评估整体质量和决定是否继续优化。

### Problem（当前问题）*

管线在 review_script 后终止，只产出 JSON 产物（文案/分镜/审查），用户无法获得任何可播放的视频内容。MVP 承诺的"导出成片初稿"未兑现。

### Proposed Options（方案建议）

| Option | Description | Pros | Cons | Recommendation |
|--------|-------------|------|------|----------------|
| A | 每步只写 artifact，手动触发下一步 | 最简实现 | 用户体验差，需反复操作 | no |
| B | 自动流水线：review_script 后自动执行全部 5 步，一步出片 | 用户无感，一步出片，与现有同步管线一致 | 单次请求耗时长（30-60s） | yes |
| C | B + 异步队列 + WebSocket 进度推送 | 体验最好 | 架构改动大，过度设计 | no |

### Selected Approach（选定方案）*

- Selected: Option B
- Decision reason: 当前管线已是同步执行，保持一致。耗时问题后续可加异步队列。
- Confirmed by: user
- Confirmed at: 2026-05-05 21:50 CST

### Scope（本次范围）*

本次包括：

- voiceover skill：基于分镜旁白文本生成 TTS 配音
- material_extract skill：从源视频切出片段
- material_match skill：将配音片段匹配到素材片段
- subtitle skill：从配音音频生成 SRT 字幕
- video_compose skill：FFmpeg 合成最终视频（画面 + 配音 + 字幕）
- StepRunner 扩展：注册 5 个新 skill 和对应的 _run_* 方法
- 管线编排：扩展 DEFAULT_STEP_KEYS，review_script 后自动执行 5 步
- ArtifactType 扩展：新增 audio、subtitle、clip、final_video
- Web 工作台：视频预览播放器和下载按钮

### Non-goals（本次不做）*

本次不包括：

- 封面生成 — 原因：属于 PC-008，独立于视频合成
- 成片质量审查（review_video）— 原因：属于 PC-008，依赖最终视频产出
- 背景音乐（BGM）— 原因：首版不做音频混合复杂度
- 转场特效 — 原因：首版用简单拼接，不做视觉特效
- 异步队列 / WebSocket 进度推送 — 原因：保持同步管线一致性，后续按需添加
- TTS 供应商切换 UI — 原因：架构保证可切换，首版只实现 edge-tts

### Open Questions（开放问题）

| Question | Impact | Owner | Blocking? |
|----------|--------|-------|-----------|
| FFmpeg 是否已安装在运行环境？ | 合成和切片步骤依赖系统 FFmpeg | architect | no（可检测并提示安装） |

## 0. 功能分类（Feature Classification）

- `complexity_tier`: `deep`
- `implementation_mode`: `extension`
- `experience_surface`: `user_visible`
  - must validate discoverability and minimal usage path
- `existing_implementation_note`: Feature 002 已交付 LLM 编导管线（script_generation → storyboard → review_script），Feature 003 已交付素材双路径（material_fetch + upload）。StepRunner 已有 skill 注册和 _run_* 方法模式。无配音、切片、匹配、字幕、合成代码。
- `lifecycle_status`: `active`
- `last_verified_commit`: null
- `implementation_paths`:
  - app/src/skills/voiceover.py — 新建
  - app/src/skills/material_extract.py — 新建
  - app/src/skills/material_match.py — 新建
  - app/src/skills/subtitle.py — 新建
  - app/src/skills/video_compose.py — 新建
  - app/src/workers/step_runner.py — 扩展
  - app/src/server/routes/video_tasks.py — 扩展
  - app/src/domain/models.py — 扩展
  - app/src/web/workbench.html — 扩展
  - app/src/web/workbench.js — 扩展

---

## 1. 用户问题（User Problem）

**核心痛点**:
当前管线只产出结构化文本（文案/分镜/审查），无法生成任何可播放的视频内容。用户评估了 AI 编导质量后，没有下一步可走。

**当前状态**:
提交任务 → 文案/分镜/审查产出 → 管线终止 → 用户只看到 JSON。

**期望状态**:
提交任务 → 文案/分镜/审查 → 配音 → 素材处理 → 字幕 → 合成 → 用户看到可播放和下载的 MP4。

---

## 2. 业务目标（Business Goal）

**主要目标**:
补完"输入主题 → 输出视频"的 MVP 闭环，让内容团队首次获得可播放、可评估的短视频初稿。

**成功指标**:
- **SI-001**: 用户提交主题 + 素材后，系统自动产出 MP4 视频文件。
- **SI-002**: 视频包含中文配音，音频时长与分镜总预估时长的偏差 < 20%。
- **SI-003**: 视频包含字幕，字幕时间轴与配音对齐。
- **SI-004**: 用户可在 Web 工作台直接播放和下载视频。

**业务价值**:
这是 MVP 的核心兑现——没有视频输出，整个平台只是一个文本生成工具。视频初稿是验证"AI 编导 → 真实视频"这个核心假设的必要条件。

---

## 3. 用户故事（User Stories）*

### US-001 - 自动生成视频初稿 (Priority: P1) 🎯 MVP

**描述**:
作为 内容团队成员，我希望 提交主题和素材后系统自动生成带配音、画面和字幕的完整视频初稿，以便 我评估整体视频质量和决定是否继续优化。

**独立测试**:
通过 API 提交任务（topic + source_links），等待管线完成后检查 final_video artifact 是否为可播放 MP4。

**验收场景（Acceptance Scenarios）**:
1. **S-001 / AC-001**: **Given** storyboard 步骤已产出分镜表, **When** 系统执行 voiceover 步骤, **Then** 生成 MP3 音频 artifact，包含完整的中文旁白配音
2. **S-002 / AC-002**: **Given** material_fetch 已下载源视频, **When** 系统执行 material_extract 步骤, **Then** 切出 clip artifacts，每个片段有起止时间和时长
3. **S-003 / AC-003**: **Given** voiceover 和 material_extract 已完成, **When** 系统执行 material_match 步骤, **Then** 每个配音片段分配到对应素材片段
4. **S-004 / AC-004**: **Given** voiceover 已生成音频, **When** 系统执行 subtitle 步骤, **Then** 生成 SRT 字幕 artifact，时间轴与音频对齐
5. **S-005 / AC-005**: **Given** material_match、voiceover 和 subtitle 已完成, **When** 系统执行 video_compose 步骤, **Then** 生成 MP4 final_video artifact，可播放

---

### US-002 - Web 工作台预览和下载视频 (Priority: P1) 🎯 MVP

**描述**:
作为 内容团队成员，我希望 在任务详情页看到视频预览和下载入口，以便 我直接在浏览器中评估视频初稿。

**独立测试**:
创建任务等待完成后，在 Web 工作台打开任务详情，验证视频播放器可播放、下载按钮可下载。

**验收场景（Acceptance Scenarios）**:
1. **S-006 / AC-006**: **Given** video_compose 已生成最终视频, **When** 用户打开任务详情页, **Then** 看到视频预览播放器和下载按钮

---

## 3.5 验收标准（Acceptance Criteria）*

- **AC-001**: System MUST generate voiceover audio (MP3) from storyboard voiceover_text using edge-tts, and persist as audio artifact.
- **AC-002**: System MUST extract clips from source video artifacts using FFmpeg, and persist as clip artifacts with start/end timestamps.
- **AC-003**: System MUST match voiceover segments to material clips based on duration, persisting the mapping as a matched_segments artifact.
- **AC-004**: System MUST generate SRT subtitle file from voiceover audio with accurate time alignment, and persist as subtitle artifact.
- **AC-005**: System MUST compose final video (MP4) with matched clips, voiceover audio, and burned-in subtitles using FFmpeg, and persist as final_video artifact.
- **AC-006**: Web workbench MUST display a video player and download button when final_video artifact exists.

---

## 4. 功能需求（Functional Requirements）*

### 核心功能
- **FR-001**: System MUST execute voiceover step after review_script, generating TTS audio from storyboard voiceover_text.
- **FR-002**: System MUST execute material_extract step after voiceover, extracting clips from source videos.
- **FR-003**: System MUST execute material_match step after material_extract, mapping clips to voiceover segments.
- **FR-004**: System MUST execute subtitle step after voiceover, generating SRT from audio transcription.
- **FR-005**: System MUST execute video_compose step after material_match + subtitle, composing final MP4.
- **FR-006**: Each media processing step MUST write artifacts (audio, clip, subtitle, final_video) with proper storage references.
- **FR-007**: Each media processing step MUST be independently retryable when it fails.

### 管线编排
- **FR-010**: DEFAULT_STEP_KEYS MUST be extended to include voiceover, material_extract, material_match, subtitle, video_compose.
- **FR-011**: Pipeline MUST execute the 5 new steps automatically after review_script completes.
- **FR-012**: When source videos are unavailable (no downloads, no upload), material_extract and material_match MUST produce a minimal video (solid color background with voiceover and subtitles).

### 错误处理
- **FR-020**: When FFmpeg is not available, system MUST fail fast with a clear error message indicating installation requirement.
- **FR-021**: When TTS generation fails, system MUST record the error and allow step retry.
- **FR-022**: When video composition fails, system MUST preserve intermediate artifacts for debugging.

---

## 5. 输入约束（Input Constraints）

本功能不引入新的用户输入字段。管线使用已有任务的 input_text 和 source_links。

**间接输入约束**:
| 数据源 | 来源步骤 | 格式要求 |
|--------|---------|---------|
| voiceover_text | storyboard segments | 非空字符串 |
| source video files | material_fetch artifacts | .mp4/.mov/.avi |
| script text | script_generation artifact | 非空字符串 |

---

## 6. 成功标准（Success Criteria）*

### 功能完整性
- **SC-001**: 提交主题 + 素材后，系统自动产出可播放的 MP4 视频文件。
- **SC-002**: 视频包含中文配音，配音内容与分镜旁白文本一致。
- **SC-003**: 视频包含字幕，字幕时间轴与配音对齐。
- **SC-004**: 用户可在 Web 工作台直接播放和下载视频。
- **SC-005**: 每个媒体处理步骤失败时可独立重试，不影响已完成的步骤。

### 性能标准
- **SC-PERF-001**: TTS 配音生成在 30 秒内完成（120 秒以内的文案）。
- **SC-PERF-002**: 视频合成在 60 秒内完成（120 秒以内的视频）。

### 质量标准
- **SC-QUAL-001**: 测试覆盖率 >= 80%
- **SC-QUAL-002**: 每个 skill 有独立的单元测试
- **SC-QUAL-003**: 端到端集成测试覆盖完整管线（提交 → MP4 产出）

## 6.5 AI Behavior Evaluation Criteria

- `applicable`: false
- `required`: false
- `eval_level`: none
- `reason`: Feature 包含 TTS（edge-tts 确定性生成）和 FFmpeg 媒体处理。Whisper ASR 为确定性转录，不涉及语义判断。

---

## 7. 范围边界（Scope）

**包含（In Scope）**:
- Story 1 (P1): 5 步媒体管线（voiceover → material_extract → material_match → subtitle → video_compose）
- Story 2 (P1): Web 视频预览和下载

**不包含（Out of Scope）**:
- 封面生成 - 原因：PC-008
- 成片质量审查 - 原因：PC-008
- 背景音乐 - 原因：首版不做音频混合
- 转场特效 - 原因：首版简单拼接
- 异步队列 - 原因：保持同步管线一致

---

## 7.1 Entry Points / Discovery Path

- Primary entry point: Web 工作台任务详情页，video_compose 完成后自动出现视频播放器和下载按钮
- Secondary entry point: API `GET /api/video-tasks/{id}/artifacts/{artifact_id}/content` 可获取 final_video artifact 元信息
- Discovery notes: 视频预览区域仅在 final_video artifact 存在时显示，不会在未完成时占位
- Minimal usage path: 提交任务 → 等待管线完成 → 任务详情页 → 播放/下载视频

---

## 8. 风险与依赖

**风险项**:
| 风险 | 缓解措施 |
|------|---------|
| FFmpeg 未安装或版本不兼容 | 启动时检测 FFmpeg 可用性，失败时给出安装指引 |
| edge-tts 中文语音质量不理想 | Skill 适配层隔离供应商，可切换到其他 TTS |
| 源视频片段总时长不足 | 素材循环拼接，或使用纯色背景降级 |
| Whisper 字幕与文案不对齐 | 使用文案辅助对齐，必要时回退到按分镜时间切分 |
| 同步管线耗时长（30-60s） | 首版可接受；后续可加异步队列 |

**外部依赖**:
- 系统级 FFmpeg 二进制
- edge-tts Python 包
- faster-whisper Python 包

---

## 9. 待澄清项

无。用户已确认全部关键决策。
