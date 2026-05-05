---
feature_id: "003"
feature_name: 素材两路径与失败分流（链接下载 + 上传替代）
created_at: 2026-05-05
created_by: /bewater-goal
status: specified
lifecycle_status: active
last_verified_commit: null
last_verified_at: null
implementation_paths:
  - app/src/workers/step_runner.py — 新增 material_fetch step handler
  - app/src/storage/sqlite.py — 新增 waiting_for_material 任务状态
  - app/src/artifacts/store.py — 扩展支持二进制文件存储
  - app/src/server/routes/video_tasks.py — 新增素材上传 API
  - app/src/web/workbench.html — 素材状态面板 + 上传 UI
  - app/src/web/workbench.js — 素材上传交互逻辑
risk_level: medium
complexity_tier: standard
implementation_mode: extension
experience_surface: user_visible
ai_behavior_eval:
  applicable: false
  required: false
  eval_level: none
  reason: N/A — 素材获取和上传是确定性文件操作，不涉及 AI/LLM/Agent 行为
  primary_risks: []
  success_threshold: N/A — no AI behavior eval required
existing_implementation_note: Feature 002 已交付 AI 编导管线（script_generation → storyboard → review_script）。source_links 作为 JSON 元数据存储但从未下载或使用。无上传 API、无二进制文件存储、无素材状态管理。需要新增 material_fetch step、上传 API、文件存储和 Web 素材交互。
rework_risk: medium
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
  confirmed_at: 2026-05-05 20:00 CST
  reviewed_items:
    - user_story
    - non_goals
    - key_scenarios
  notes: 用户已确认素材获取层级（独立 Workflow Step）、素材类型（视频片段为主）、失败分流策略（暂停等待上传）、pipeline 排序（material_fetch 在 script_generation 之前）。
split_assessment:
  user_value_points: 2
  scenarios_count: 3
  impacted_modules_count: 4
  unresolved_clarifications_count: 0
  complex_scenario_dependencies: false
  triggered_conditions: []
  decision: proceed
  override_by: null
  override_reason: N/A — no split conditions triggered
scenarios:
  - id: S-001
    story_id: US-001
    title: 系统自动下载素材链接并展示获取状态
    given: 用户在创建任务时提供了至少一个素材链接
    when: 系统执行 material_fetch 步骤尝试下载每个链接
    then: Web 上展示每个素材的获取状态（下载中/成功/失败）及失败原因
    acceptance_refs: AC-001
  - id: S-002
    story_id: US-002
    title: 素材下载失败时任务暂停并提示用户上传
    given: material_fetch 步骤中所有素材链接下载失败
    when: 系统将任务状态设为 waiting_for_material
    then: Web 上明确展示每个素材的失败原因（不可达/格式不支持/大小超限/超时/平台限制），并提供上传入口
    acceptance_refs: AC-002
  - id: S-003
    story_id: US-003
    title: 用户上传替代素材后任务自动继续
    given: 任务处于 waiting_for_material 状态
    when: 用户通过 Web 上传视频文件替代失败的素材
    then: material_fetch 步骤完成，任务状态恢复为 running，后续 pipeline 步骤自动执行
    acceptance_refs: AC-003
---

# 功能：素材两路径与失败分流（链接下载 + 上传替代）

> **用途**: 定义功能的目标和验收标准
>
> **LLM 行为约束**:
> - ✅ 只描述 WHAT（做什么）和 WHY（为什么做）
> - ❌ 不描述 HOW（怎么做）— 技术细节属于 design.md / tasks.md

## Product Decision Summary（产品决策摘要）

### Goal（用户结果）*

内容团队提交素材链接后，系统自动尝试下载视频片段；下载失败时给出明确结构化原因，任务暂停等待用户上传替代素材，上传后自动继续后续 pipeline。

### Vision Link（服务愿景）*

- Vision section: Open Assumptions + Direction / Now
- Link reason: Vision 明确指出"用户提供的视频链接可被系统下载或解析；若链接平台限制下载，需要支持用户上传素材或人工导入作为替代"——这是当前首要外部不确定性的工程化降级。

### User Scenario（触发场景）*

内容团队成员创建视频任务时提供了素材链接（如视频片段 URL），需要系统自动获取这些素材，如果链接不可用则通过上传方式补充，确保任务不因素材问题而中断。

### Problem（当前问题）*

Feature 002 交付后，系统接受 `source_links` 但只存为 JSON 元数据，从不下载或使用。素材可用性是完全的黑盒——用户不知道链接是否能下载，下载失败时没有任何反馈或替代路径。这是端到端可用性的首要外部风险。

### Proposed Options（方案建议）

| Option | Description | Pros | Cons | Recommendation |
|--------|-------------|------|------|----------------|
| A | 只加错误提示，不下载素材 | 改动最小 | 没有实际下载能力，"失败原因"无法给出 | no |
| B | 新增 material_fetch step + 上传替代 + 文件存储 | 完整解决"链接失败怎么办"，符合 Artifact-First 原则 | 需要新增文件存储、上传 API、下载逻辑 | yes |
| C | 同 B + 素材质量预检（分辨率/时长） | 更完善的质量把控 | 增加媒体解析依赖，当前 pipeline 不消费素材，预检价值有限 | no |

### Selected Approach（选定方案）*

- Selected: Option B
- Decision reason: 完整解决"链接失败怎么办"的核心问题，同时不过度扩展到素材质量评估——当前 pipeline 尚不消费素材，质量预检价值有限。
- Confirmed by: user
- Confirmed at: 2026-05-05 20:00 CST

### Scope（本次范围）*

本次包括：

- 新增 `material_fetch` workflow step，尝试下载 source_links 中的视频片段
- 每个链接独立处理，记录结构化错误（不可达 / 格式不支持 / 大小超限 / 超时 / 平台限制）
- `waiting_for_material` 任务状态，素材全部获取失败时暂停等待上传
- 新增文件上传 API（multipart/form-data）
- Web 工作台新增素材状态面板（每条链接的获取状态和失败原因）
- Web 工作台新增素材上传交互（选择文件上传）
- 素材存储为二进制文件，扩展 artifact store 支持
- Pipeline 顺序：input → material_fetch → script_generation → storyboard → review_script

### Non-goals（本次不做）*

本次不包括：

- 素材质量评估（分辨率/时长/清晰度验证）— 原因：当前 pipeline 不消费素材，评估结果无消费方
- 素材与分镜自动匹配 — 原因：属于后续 feature，需要先有消费素材的 pipeline 步骤
- 图片/音频素材支持 — 原因：首版聚焦视频片段主场景，其他类型后续迭代
- 素材库管理（复用/清理/去重）— 原因：属于独立 feature，当前只需基本存储
- 修改现有 pipeline 步骤 — 原因：script/storyboard/review 不消费素材，无需改动

### Open Questions（开放问题）

| Question | Impact | Owner | Blocking? |
|----------|--------|-------|-----------|
| 素材文件大小上限？ | 影响存储和上传 API 设计 | architect | no（建议首版 500MB） |
| 下载超时时间？ | 影响用户体验 | architect | no（建议首版 60s per link） |

## 0. 功能分类（Feature Classification）

- `complexity_tier`: `standard`
- `implementation_mode`: `extension`
- `experience_surface`: `user_visible`
  - must validate discoverability and minimal usage path
- `existing_implementation_note`: Feature 002 已交付 AI 编导管线。当前入口：`app/src/workers/step_runner.py`（script/storyboard/review 步骤）、`app/src/server/routes/video_tasks.py`（API routes）、`app/src/web/workbench.html`（工作台 UI）、`app/src/artifacts/store.py`（JSON artifact 存储）。已知缺口：无素材下载逻辑、无上传 API、无二进制文件存储、无素材状态管理。不接近完成。
- `lifecycle_status`: `active`
- `last_verified_commit`: null
- `implementation_paths`:
  - app/src/workers/step_runner.py — 新增 material_fetch step handler
  - app/src/storage/sqlite.py — 新增 waiting_for_material 任务状态
  - app/src/artifacts/store.py — 扩展支持二进制文件存储
  - app/src/server/routes/video_tasks.py — 新增素材上传 API
  - app/src/web/workbench.html — 素材状态面板 + 上传 UI
  - app/src/web/workbench.js — 素材上传交互逻辑

---

## 0.1 显式空值约定（Explicit N/A Contract）

> Blank critical fields mean "not evaluated".
> If a field was evaluated and does not apply, write `N/A — reason`.

N/A — all critical fields have been evaluated and filled.

## 0.2 返工风险与拆分评估

- `complexity_tier`: standard — 涉及文件存储、HTTP 下载、上传 API、Web UI 变更
- `risk_level`: medium — 引入文件存储和上传，有容量/安全考量
- `rework_risk`: medium — 存储方案设计不当可能需要重构，但影响范围可控

Split assessment: 无 split 条件被触发（user_value_points=2, scenarios_count=3, impacted_modules_count=4, unresolved_clarifications=0, no complex dependencies）。

---

## 1. 用户问题（User Problem）

**核心痛点**:
素材链接的可用性是黑盒——用户不知道链接能否下载，下载失败时没有任何反馈或替代路径，导致后续 pipeline 在没有素材的情况下空转。

**当前状态**:
source_links 作为 JSON 元数据存储，从不下载或使用。用户无法判断素材是否可用，也无法在链接失败时提供替代素材。

**期望状态**:
系统自动尝试下载素材链接，给出每个素材的获取状态和失败原因；失败时允许用户上传替代素材，确保任务不因外部链接问题而中断。

---

## 2. 业务目标（Business Goal）

**主要目标**:
把"素材不可用"从偶发 bug 变成可管理分支——用户始终能获得明确的素材获取反馈，并拥有上传替代路径。

**成功指标**:
- **SI-001**: 系统能自动尝试下载用户提供的素材链接，并展示每个链接的获取结果。
- **SI-002**: 素材下载失败时，用户能在 Web 上看到结构化的失败原因。
- **SI-003**: 用户能通过上传方式替代失败的素材，上传后任务自动继续。

**业务价值**:
素材可用性是视频自动化生产的首要外部不确定性。没有可靠的素材获取和降级路径，整个端到端 pipeline 的可用性无法保证。

---

## 3. 用户故事（User Stories）*

### US-001 - 系统自动获取素材链接 (Priority: P1) 🎯 MVP

**描述**:
作为 内容团队成员，我希望 提交素材链接后系统自动尝试下载视频片段并在 Web 上展示获取状态，以便 我知道哪些素材可用、哪些有问题。

**独立测试**:
创建带 source_links 的任务，验证 material_fetch 步骤执行后 Web 展示每个链接的下载状态（成功/失败+原因）。

**验收场景（Acceptance Scenarios）**:
1. **S-001 / AC-001**: **Given** 用户在创建任务时提供了至少一个素材链接, **When** 系统执行 material_fetch 步骤, **Then** Web 上展示每个素材的获取状态（下载中/成功/失败），失败时包含结构化原因（不可达/格式不支持/大小超限/超时/平台限制）

---

### US-002 - 素材失败时任务暂停等待上传 (Priority: P1) 🎯 MVP

**描述**:
作为 内容团队成员，我希望 素材全部下载失败时任务暂停并明确提示我上传，以便 我能提供替代素材继续推进。

**独立测试**:
创建任务并提供全部不可下载的链接，验证任务进入 waiting_for_material 状态，Web 显示失败原因和上传入口。

**验收场景（Acceptance Scenarios）**:
1. **S-002 / AC-002**: **Given** material_fetch 步骤中所有素材链接下载失败, **When** 系统将任务状态设为 waiting_for_material, **Then** Web 上展示每个素材的失败原因，并提供文件上传入口

---

### US-003 - 上传替代素材后任务自动继续 (Priority: P1) 🎯 MVP

**描述**:
作为 内容团队成员，我希望 上传本地视频文件替代失败的素材后任务自动继续，以便 我不需要重新创建任务。

**独立测试**:
任务处于 waiting_for_material 状态时上传视频文件，验证 material_fetch 步骤完成、任务状态恢复为 running、后续 pipeline 步骤自动执行。

**验收场景（Acceptance Scenarios）**:
1. **S-003 / AC-003**: **Given** 任务处于 waiting_for_material 状态, **When** 用户通过 Web 上传视频文件替代失败的素材, **Then** material_fetch 步骤标记为完成，任务恢复 running 状态，后续步骤自动执行

---

## 3.5 验收标准（Acceptance Criteria）*

- **AC-001**: System MUST attempt to download each source link as a video file during the material_fetch step and record per-link status (downloading/success/failed) with structured failure reasons (unreachable, unsupported_format, size_exceeded, timeout, platform_restriction).
- **AC-002**: When ALL source links fail to download, System MUST set task status to `waiting_for_material` and persist per-link failure details as a material_fetch artifact; Web MUST display each failure reason and provide a file upload entry point.
- **AC-003**: System MUST provide a file upload API accepting video files (multipart/form-data); after successful upload, the material_fetch step MUST complete and the task MUST resume to running status, triggering subsequent pipeline steps.

---

## 4. 功能需求（Functional Requirements）*

### 核心功能
- **FR-001**: System MUST execute a `material_fetch` step that attempts to download each URL in `source_links` as a video file.
- **FR-002**: System MUST process each source link independently — success of one link MUST NOT depend on the success of others.
- **FR-003**: System MUST record a structured error for each failed download with category (unreachable, unsupported_format, size_exceeded, timeout, platform_restriction) and a human-readable message.
- **FR-004**: When ALL source links fail, System MUST set task status to `waiting_for_material`.
- **FR-005**: When at least one source link succeeds, System MUST complete the material_fetch step and allow the pipeline to continue.
- **FR-006**: System MUST store downloaded video files as binary artifacts with metadata (source_url, file_size, content_type, downloaded_at).

### 上传替代
- **FR-010**: System MUST provide a file upload API endpoint accepting multipart/form-data with video files.
- **FR-011**: Upload API MUST accept video formats: mp4, mov, avi (configurable allowlist).
- **FR-012**: Upload API MUST enforce a maximum file size (default 500MB, configurable).
- **FR-013**: After successful upload, System MUST mark the material_fetch step as complete and resume the task pipeline.
- **FR-014**: System MUST store uploaded files as binary artifacts with metadata (upload_source, file_size, content_type, uploaded_at).

### Web 工作台
- **FR-020**: Web workbench MUST display a material status panel in task detail view showing each source link's status and failure reason.
- **FR-021**: Web workbench MUST display a file upload interface when task status is `waiting_for_material`.
- **FR-022**: Web workbench MUST show upload progress feedback during file upload.
- **FR-023**: Web workbench MUST update material status in real-time after upload completes.

### 错误处理
- **FR-030**: When download encounters a network error, System MUST categorize it as `unreachable` or `timeout`.
- **FR-031**: When downloaded file is not a supported video format, System MUST categorize it as `unsupported_format`.
- **FR-032**: When downloaded file exceeds size limit, System MUST categorize it as `size_exceeded`.
- **FR-033**: When download succeeds but content indicates platform restriction (e.g., auth wall), System MUST categorize it as `platform_restriction`.

---

## 5. 输入约束（Input Constraints）

| 字段 | 最大长度 | 格式要求 | 默认值 |
|------|---------|---------|-------|
| source_links | 每行 2048 字符，最多 10 行 | 每行一个 URL（http/https） | 空列表 |
| upload file | 500 MB | mp4, mov, avi | 无 |
| failure_category | — | 枚举：unreachable, unsupported_format, size_exceeded, timeout, platform_restriction | 无 |

**补充规则**:
- source_links 为可选字段，可留空（此时 material_fetch 步骤跳过或直接通过）
- 上传文件格式通过 Content-Type 和文件扩展名双重校验
- 上传文件大小通过 Content-Length 预检 + 实际写入校验

---

## 6. 成功标准（Success Criteria）*

### 功能完整性
- **SC-001**: material_fetch 步骤能正确下载可达的视频链接并存储为二进制 artifact。
- **SC-002**: 不可达/格式错误/超时的链接能产生结构化错误信息，Web 可展示。
- **SC-003**: 素材全部失败时任务进入 waiting_for_material 状态。
- **SC-004**: 用户上传文件后任务自动恢复并继续 pipeline。

### 性能标准
- **SC-PERF-001**: 单个链接下载在 60 秒内完成或超时。
- **SC-PERF-002**: 文件上传支持至少 500MB 文件。

### 质量标准
- **SC-QUAL-001**: 测试覆盖率 >= 80%
- **SC-QUAL-002**: 上传 API 有安全校验测试（文件类型、大小）
- **SC-QUAL-003**: 下载错误分类有单元测试覆盖

## 6.5 AI Behavior Evaluation Criteria

### AI Eval Non-Applicability Reason

- N/A — 素材获取和上传是确定性文件操作（HTTP 下载 + multipart 上传 + 文件存储），不涉及 AI/LLM/Agent 行为。

---

## 7. 范围边界（Scope）

**包含（In Scope）**:
- Story 1 (P1): 素材链接自动下载 + 状态展示
- Story 2 (P1): 失败分流 + 任务暂停等待上传
- Story 3 (P1): 上传替代 + 任务自动继续

**不包含（Out of Scope）**:
- 素材质量评估 - 原因：当前 pipeline 不消费素材，评估无消费方
- 素材与分镜匹配 - 原因：需要先有消费素材的步骤
- 图片/音频支持 - 原因：首版聚焦视频片段
- 素材库管理 - 原因：独立 feature
- 现有步骤修改 - 原因：script/storyboard/review 不消费素材

---

## 7.1 Entry Points / Discovery Path

- Primary entry point: Web 工作台任务详情页，素材状态面板自动展示
- Secondary entry point: API `POST /api/video-tasks/{task_id}/materials`，上传素材文件
- Discovery notes: 用户创建带 source_links 的任务后，material_fetch 步骤自动执行；失败时 Web 显示上传入口
- Minimal usage path: 创建任务（带链接）→ 查看素材状态 → 失败时上传 → 任务继续

---

## 8. 风险与依赖

**风险项**:
| 风险 | 缓解措施 |
|------|---------|
| 素材平台反爬/限流 | 结构化错误分类（platform_restriction）+ 上传替代路径 |
| 上传文件安全风险 | 文件类型白名单 + 大小限制 + 文件名清理 |
| 存储容量增长 | 首版不自动清理，记录清理策略为后续 feature |
| 下载超时阻塞 pipeline | 每链接独立超时（60s）+ 并行下载 |

**外部依赖**:
- HTTP 客户端库（aiohttp/httpx 用于下载）
- 现有 Feature 002 任务骨架和 artifact 系统
- 本地文件系统存储空间

---

## 9. 待澄清项

无未解决的澄清项。所有关键决策已确认。

---

## 实现位置（完成后填写）

| 功能 | 代码位置 | 测试位置 |
|------|---------|---------|
| material_fetch step | `path/to/file.py:line` | `tests/xxx.test.py:line` |
| 上传 API | `path/to/file.py:line` | `tests/xxx.test.py:line` |
| 素材存储 | `path/to/file.py:line` | `tests/xxx.test.py:line` |
| Web 素材 UI | `path/to/file.py:line` | `tests/xxx.test.py:line` |
