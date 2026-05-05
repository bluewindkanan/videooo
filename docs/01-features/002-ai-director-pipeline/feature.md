---
feature_id: "002"
feature_name: AI 编导管线（LLM 文案/分镜/审查 + 可用 Web 工作台）
created_at: 2026-05-05
created_by: /bewater-goal
status: specified
lifecycle_status: active
last_verified_commit: null
last_verified_at: null
implementation_paths:
  - app/src/workers/step_runner.py — 替换占位符为真实 LLM 调用
  - app/src/skills/ — 新增 skill 实现（script_generation, storyboard, review_script）
  - app/src/web/ — 升级工作台 UI
  - app/src/server/routes/video_tasks.py — 新增步骤和产物 API
  - app/src/domain/models.py — 可能需要扩展 artifact 类型
risk_level: medium
complexity_tier: standard
implementation_mode: extension
experience_surface: user_visible
ai_behavior_eval:
  applicable: true
  required: true
  eval_level: standard
  reason: 编导 Agent 直接生成用户可见的文案和分镜，Reviewer Agent 审查结果影响用户判断是否继续后续媒体步骤。LLM 输出质量直接影响产品可信度。
  primary_risks:
    - 文案跑题或事实错误导致错误传播到后续媒体步骤
    - 分镜描述过于模糊导致后续素材匹配无法落地
    - Reviewer 漏判导致用户误以为质量达标
    - LLM 输出格式不稳定导致解析失败
  success_threshold: 文案结构合规率 >= 0.9，分镜包含必需字段且语义相关 >= 0.8，Review findings 能发现注入的已知问题
existing_implementation_note: Feature 001 已交付任务骨架（FastAPI + SQLite + 占位 StepRunner + 最小 Web 工作台）。StepRunner 当前为确定性占位符，需替换为真实 LLM 调用。已有步骤：script_generation, review_script。需新增 storyboard 步骤。Web 工作台为最小 HTML/JS，需升级为可用级（任务列表 + 卡片式步骤 + 可读产物展示）。
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
  confirmed_at: 2026-05-05 18:10 CST
  reviewed_items:
    - user_story
    - non_goals
    - key_scenarios
  notes: 用户已确认 AI 编导管线的 user story（文案+分镜+审查+任务列表）、non-goals（不做 TTS/字幕/合成/编辑）和 key scenarios（S-001~S-004）。
split_assessment:
  user_value_points: 3
  scenarios_count: 4
  impacted_modules_count: 3
  unresolved_clarifications_count: 0
  complex_scenario_dependencies: false
  triggered_conditions: []
  decision: proceed
  override_by: null
  override_reason: N/A — no split conditions triggered
scenarios:
  - id: S-001
    story_id: US-001
    title: 输入主题后 LLM 生成完整短视频文案
    given: 用户在 Web 工作台输入主题或文案
    when: 提交任务后系统调用真实 LLM 执行 script_generation 步骤
    then: Web 上以可读格式展示包含 hook、body、call_to_action 的完整文案，且文案与输入主题语义相关
    acceptance_refs: AC-001
  - id: S-002
    story_id: US-001
    title: 基于文案自动生成分镜表
    given: script_generation 步骤已完成并产出文案
    when: 系统自动执行 storyboard 步骤
    then: Web 上展示分镜表，每个分镜包含旁白文本、画面意图、预估时长，且与文案内容对应
    acceptance_refs: AC-002
  - id: S-003
    story_id: US-001
    title: Reviewer 审查文案和分镜并输出问题清单
    given: 文案和分镜已生成
    when: 系统执行 review_script 步骤
    then: Web 上展示带 stage/severity/location/message 的问题清单；若无问题则明确标注通过
    acceptance_refs: AC-003
  - id: S-004
    story_id: US-002
    title: 在任务列表中查看和选择任务
    given: 用户已有至少一个已创建的视频任务
    when: 用户打开 Web 工作台
    then: 看到任务列表，可点击进入任务详情查看步骤状态和产物
    acceptance_refs: AC-004
---

# 功能：AI 编导管线（LLM 文案/分镜/审查 + 可用 Web 工作台）

> **用途**: 定义功能的目标和验收标准
>
> **LLM 行为约束**:
> - ✅ 只描述 WHAT（做什么）和 WHY（为什么做）
> - ❌ 不描述 HOW（怎么做）— 技术细节属于 design.md / tasks.md

## Product Decision Summary（产品决策摘要）

### Goal（用户结果）*

内容团队成员输入主题/文案/链接后，能在 Web 工作台上看到 AI 生成的完整短视频文案、分镜表和 Review 问题清单，以可读格式评估 AI 编导质量，决定是否继续后续配音和合成步骤。

### Vision Link（服务愿景）*

- Vision section: Narrowest Wedge + Direction / Now + Core Promise
- Link reason: 这个 feature 直接验证"编导 Agent 能否生成可用短视频文案和分镜"（Vision Now 第 2 条），是 Vision Core Promise 中"输入主题后得到可预览初稿"的前半段核心能力。

### User Scenario（触发场景）*

内容团队成员要把一篇文章或一个主题快速变成知识分享短视频，需要在提交任务后先看到 AI 生成的文案和分镜是否靠谱，再决定是否继续投入后续媒体制作。

### Problem（当前问题）*

Feature 001 交付了任务骨架，但 StepRunner 是确定性占位符（只返回模板文案），Web 工作台只显示原始 JSON。内容团队无法评估 AI 编导的真实质量，无法做出"是否继续"的判断。

### Proposed Options（方案建议）

| Option | Description | Pros | Cons | Recommendation |
|--------|-------------|------|------|----------------|
| A | 只替换 StepRunner 为真实 LLM，不升级 Web | 改动最小 | 用户仍看 JSON，无法有效评估 | no |
| B | 替换 StepRunner + 升级 Web 工作台为可用级 | 用户能以可读格式评估 AI 产出 | 需要前后端同时改动 | yes |
| C | 替换 StepRunner + 富文本编辑器 + 可编辑文案 | 用户体验最好 | 范围过大，富文本编辑器是另一个 feature | no |

### Selected Approach（选定方案）*

- Selected: Option B
- Decision reason: 用户需要可读格式来评估 AI 产出，但不需要编辑能力——编辑能力属于后续 feature。
- Confirmed by: user
- Confirmed at: 2026-05-05 18:10 CST

### Scope（本次范围）*

本次包括：

- 接入国产 LLM（通义千问/智谱 GLM）替代占位符 StepRunner
- script_generation 步骤调用 LLM 生成完整短视频文案（hook + body + call_to_action + 预估时长）
- 新增 storyboard 步骤调用 LLM 基于文案生成分镜表（旁白文本 + 画面意图 + 关键词 + 预估时段）
- review_script 步骤调用 LLM 审查文案和分镜，输出结构化问题清单
- Web 工作台升级：任务列表、卡片式步骤状态、文案/分镜可读展示、Review 问题清单展示
- LLM 调用通过 Skill 适配层隔离，支持后续切换供应商

### Non-goals（本次不做）*

本次不包括：

- TTS 配音、字幕生成、视频合成 — 原因：属于 Feature 003/004，先验证 AI 编导质量。
- 素材下载和匹配 — 原因：不确定性最高，MVP 阶段不涉及。
- 文案/分镜的在线编辑 — 原因：编辑能力是独立 feature，本次只做可读展示。
- 封面生成 — 原因：属于后续 feature。
- 成片 Review — 原因：依赖视频合成，属于 Feature 004。

### Open Questions（开放问题）

| Question | Impact | Owner | Blocking? |
|----------|--------|-------|-----------|
| 使用通义千问还是智谱 GLM？还是两者都支持通过 Skill adapter 切换？ | 影响初始 adapter 实现和成本 | architect | no（首版选一个，架构保证可切换） |

## 0. 功能分类（Feature Classification）

- `complexity_tier`: `standard`
- `implementation_mode`: `extension`
- `experience_surface`: `user_visible`
  - must validate discoverability and minimal usage path
- `existing_implementation_note`: Feature 001 已交付任务骨架。当前入口：`app/src/workers/step_runner.py`（占位符 StepRunner）、`app/src/web/workbench.html`（最小 HTML）、`app/src/server/routes/video_tasks.py`（API routes）。已知缺口：无真实 LLM 调用、无 storyboard 步骤、Web 不可用。不接近完成。
- `lifecycle_status`: `active`
- `last_verified_commit`: null
- `implementation_paths`:
  - app/src/workers/step_runner.py — 替换占位符为真实 LLM 调用
  - app/src/skills/ — 新增 skill 实现
  - app/src/web/ — 升级工作台 UI
  - app/src/server/routes/video_tasks.py — 新增步骤和产物 API

---

## 1. 用户问题（User Problem）

**核心痛点**:
当前任务骨架的 AI 编导是占位符，内容团队无法评估真实 LLM 生成的文案和分镜质量，无法判断"AI 编导到底靠不靠谱"。

**当前状态**:
提交任务后 StepRunner 返回模板文案（`关于：xxx`），Web 显示原始 JSON，无法用于实际内容评估。

**期望状态**:
提交任务后系统调用真实 LLM 生成完整的短视频文案、分镜表和 Review 结果，Web 以可读格式展示，内容团队可以评估质量并决定下一步。

---

## 2. 业务目标（Business Goal）

**主要目标**:
验证 AI 编导 Agent 能否生成可用于后续媒体制作的短视频文案和分镜，同时让内容团队在 Web 上完成"提交→查看→评估"的最小可用闭环。

**成功指标**:
- **SI-001**: 用户能在 Web 工作台上看到 AI 生成的完整文案（hook/body/CTA）和分镜表。
- **SI-002**: 文案与输入主题语义相关，分镜与文案内容对应。
- **SI-003**: Reviewer 能发现文案和分镜中的已知问题（如跑题、结构缺失）。
- **SI-004**: 用户能在任务列表中浏览所有任务，点击查看详情。

**业务价值**:
验证 AI 编导质量是整个视频自动化生产平台的前提——如果文案和分镜不可用，后续配音、合成都无法产生有价值的成片。

---

## 3. 用户故事（User Stories）*

### US-001 - AI 生成文案/分镜并展示结果 (Priority: P1) 🎯 MVP

**描述**:
作为 内容团队成员，我希望 输入主题后系统调用真实 LLM 生成短视频文案和分镜，并在 Web 上以可读格式展示，以便 我评估 AI 编导质量。

**独立测试**:
通过 Web 提交任务，验证 Web 上展示的文案包含 hook/body/CTA 且与输入相关；分镜表包含旁白/画面/时长且与文案对应。

**验收场景（Acceptance Scenarios）**:
1. **S-001 / AC-001**: **Given** 用户输入主题或文案, **When** 系统执行 script_generation 步骤, **Then** Web 展示完整文案（hook + body + call_to_action + 预估时长），且文案与输入主题语义相关
2. **S-002 / AC-002**: **Given** 文案已生成, **When** 系统执行 storyboard 步骤, **Then** Web 展示分镜表，每个分镜包含旁白文本、画面意图和预估时段
3. **S-003 / AC-003**: **Given** 文案和分镜已生成, **When** 系统执行 review_script 步骤, **Then** Web 展示结构化问题清单（stage/severity/location/message/suggested_fix）

---

### US-002 - 任务列表与导航 (Priority: P1) 🎯 MVP

**描述**:
作为 内容团队成员，我希望 在 Web 工作台上看到所有任务列表并点击查看详情，以便 我跟踪和管理多个视频任务。

**独立测试**:
创建多个任务后刷新工作台，验证任务列表显示所有任务；点击任务可跳转到详情页查看步骤状态和产物。

**验收场景（Acceptance Scenarios）**:
1. **S-004 / AC-004**: **Given** 系统中存在至少一个视频任务, **When** 用户打开 Web 工作台, **Then** 看到任务列表（含任务 ID、状态、创建时间），点击可进入详情

---

## 3.5 验收标准（Acceptance Criteria）*

- **AC-001**: System MUST call a real LLM for script_generation and persist a script artifact containing hook, body, call_to_action, and estimated_duration_seconds that is semantically relevant to the user's input.
- **AC-002**: System MUST execute a storyboard step after script_generation, generating at least one StoryboardSegment per script section with voiceover_text, visual_intent, and estimated time range.
- **AC-003**: System MUST execute review_script using a real LLM and persist structured findings with stage, severity, location_ref, message, and suggested_fix; findings MUST detect injected known issues in test scenarios.
- **AC-004**: Web workbench MUST display a task list with task ID, status, and creation time, and allow navigation to task detail view.

---

## 4. 功能需求（Functional Requirements）*

### 核心功能
- **FR-001**: System MUST call a real LLM (domestic model: Tongyi Qianwen or Zhipu GLM) for script_generation, replacing the deterministic placeholder.
- **FR-002**: System MUST generate structured script output containing hook, body, call_to_action, and estimated_duration_seconds.
- **FR-003**: System MUST execute a storyboard step that generates a sequence of StoryboardSegments based on the script.
- **FR-004**: Each StoryboardSegment MUST contain voiceover_text, visual_intent, expected_keywords, estimated_start_seconds, and estimated_end_seconds.
- **FR-005**: System MUST execute review_script using a real LLM that evaluates script and storyboard quality.
- **FR-006**: Review findings MUST be structured as items with stage, severity, location_ref, message, and suggested_fix.
- **FR-007**: LLM calls MUST be isolated behind a Skill adapter interface, allowing provider switching without modifying workflow logic.

### Web 工作台
- **FR-010**: Web workbench MUST display a task list page showing all video tasks with ID, status, and creation time.
- **FR-011**: Web workbench MUST provide a task detail view with step status cards showing each step's status, progress, and error info.
- **FR-012**: Web workbench MUST render script artifacts in a readable format (not raw JSON).
- **FR-013**: Web workbench MUST render storyboard as a table or card list with voiceover text, visual intent, and time ranges.
- **FR-014**: Web workbench MUST render review findings as a structured issue list with severity badges.

### 错误处理
- **FR-020**: When LLM call fails, System MUST record the error with category (rate_limit, api_error, parse_error, content_filter) and a human-readable message.
- **FR-021**: When LLM output cannot be parsed into expected schema, System MUST save the raw LLM response as an llm_raw artifact for debugging.

---

## 5. 输入约束（Input Constraints）

| 字段 | 最大长度 | 格式要求 | 默认值 |
|------|---------|---------|-------|
| input_text | 5000 | 非空（当 input_kind=topic 或 draft 时） | 无 |
| article_url | 2048 | URL 格式（当 input_kind=article_url 时） | 无 |
| source_links | 每行 2048，最多 10 行 | 每行一个 URL | 空列表 |

**补充规则**:
- input_text 为空且 input_kind 不为 article_url 时应拒绝创建
- source_links 为可选字段，可留空

---

## 6. 成功标准（Success Criteria）*

### 功能完整性
- **SC-001**: 用户能在 Web 上看到 LLM 生成的完整文案、分镜和 Review 结果。
- **SC-002**: 任务列表正确显示所有任务，点击可进入详情。
- **SC-003**: 所有 LLM 步骤失败时保留原始响应和错误原因，支持重试。

### 性能标准
- **SC-PERF-001**: script_generation 步骤在 LLM API 正常情况下 30 秒内完成。
- **SC-PERF-002**: storyboard 步骤在 LLM API 正常情况下 30 秒内完成。

### 质量标准
- **SC-QUAL-001**: 测试覆盖率 >= 80%
- **SC-QUAL-002**: 所有 API 接口有集成测试
- **SC-QUAL-003**: AI 行为有 eval 样例覆盖文案质量、分镜结构和 Review 发现能力

## 6.5 AI Behavior Evaluation Criteria

- `applicable`: true
- `required`: true
- `eval_level`: standard
- `success_threshold`: 文案结构合规 >= 0.9，分镜必需字段完整 >= 0.85，Review 能发现注入的已知问题

| Dimension | Expected Behavior | Blocking Failure Class | Example Evidence |
|-----------|-------------------|------------------------|------------------|
| accuracy | Script content matches input topic without factual errors | hallucination | Golden case: input "量子计算入门" → script covers quantum computing, not classical computing |
| relevance | Storyboard segments directly correspond to script sections | irrelevant_output | Rubric: each segment maps to a script section with matching voiceover text |
| safety | Unsafe or prohibited content is flagged by reviewer | unsafe_output | Adversarial case: input with harmful content → reviewer flags it |
| format | LLM output conforms to expected JSON schema | format_violation | Schema validation on all LLM outputs |
| grounding | Review findings reference specific script/storyboard locations | ungrounded_claim | Each finding has a valid location_ref pointing to actual content |

---

## 7. 范围边界（Scope）

**包含（In Scope）**:
- Story 1 (P1): AI 编导（文案 + 分镜 + 审查）
- Story 2 (P1): 任务列表与可用级 Web 工作台

**不包含（Out of Scope）**:
- TTS 配音 - 原因：Feature 003
- 字幕生成 - 原因：Feature 003
- 视频合成 - 原因：Feature 004
- 素材下载和匹配 - 原因：MVP 后
- 文案/分镜在线编辑 - 原因：独立 feature
- 封面生成 - 原因：后续 feature

---

## 7.1 Entry Points / Discovery Path

- Primary entry point: Web 工作台首页 `/workbench`，默认显示任务列表
- Secondary entry point: API `/api/video-tasks`，可通过 API 直接创建任务
- Discovery notes: 用户打开 `/workbench` 即可看到任务列表和"创建新任务"入口
- Minimal usage path: 打开工作台 → 输入主题 → 点击创建 → 查看文案/分镜/Review 结果

---

## 8. 风险与依赖

**风险项**:
| 风险 | 缓解措施 |
|------|---------|
| LLM 输出格式不稳定 | Schema 校验 + 保存 raw response 供调试 + 重试机制 |
| LLM API 不可用或限流 | 错误分类 + 失败留痕 + 支持单步重试 |
| 国产模型中文质量不如预期 | Skill adapter 隔离供应商，可切换到其他模型 |
| Web 升级范围蔓延 | 严格限制为可读展示，不做编辑能力 |

**外部依赖**:
- 国产 LLM API（通义千问或智谱 GLM）
- 现有 Feature 001 任务骨架和数据模型

---

## 9. 待澄清项

- [ ] **[RESOLVED]** LLM 供应商: 国产模型（通义/智谱），首版选一个，架构保证可切换
