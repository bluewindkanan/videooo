---
feature_id: "001"
feature_name: 知识分享视频任务骨架（任务 / 步骤 / 产物）
created_at: 2026-05-05
created_by: /bewater-goal
status: specified
lifecycle_status: active
last_verified_commit: null
last_verified_at: null
implementation_paths:
  - N/A — not implemented yet
risk_level: medium
complexity_tier: standard
implementation_mode: greenfield
experience_surface: user_visible
ai_behavior_eval:
  applicable: true
  required: true
  eval_level: lite
  reason: 编导与 Reviewer 输出直接影响用户可见产物（文案/分镜/问题清单），且会驱动后续媒体处理步骤。
  primary_risks:
    - 文案跑题/事实错误导致错误传播
    - Reviewer 误判导致“看起来通过但不可用”
    - 输出不稳定导致流程不可重试/不可审查
  success_threshold: 见 design.md 的 AI Behavior Evaluation Strategy（lite：schema 合规 + 最小质量阈值）
existing_implementation_note: N/A — greenfield feature
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
  confirmed_at: 2026-05-05 16:44 CST
  reviewed_items:
    - user_story
    - non_goals
    - key_scenarios
  notes: 用户已确认首个切片以 FSC-001 落地，并接受“可审阅中间产物 + 可重试骨架”的范围定义。
split_assessment:
  user_value_points: 2
  scenarios_count: 2
  impacted_modules_count: 3
  unresolved_clarifications_count: 1
  complex_scenario_dependencies: false
  triggered_conditions: []
  decision: proceed
  override_by: null
  override_reason: N/A — split override not used
scenarios:
  - id: S-001
    story_id: US-001
    title: 创建知识分享视频任务并生成首个可审阅产物
    given: 内容团队成员准备好主题/文案/文章链接与素材链接
    when: 用户在 Web 工作台提交任务
    then: 系统创建任务、生成至少一个可审阅中间产物，并可查询步骤状态与产物清单
    acceptance_refs: AC-001
  - id: S-002
    story_id: US-001
    title: 单步重试与失败留痕
    given: 某一步执行失败且产生可读错误原因
    when: 用户对失败步骤执行 retry
    then: 系统保留历史产物与错误上下文，并允许该步骤重新执行直至成功或明确不可重试
    acceptance_refs: AC-002
---

# 功能：知识分享视频任务骨架（任务 / 步骤 / 产物）

> **用途**: 定义功能的目标和验收标准  
>
> **LLM 行为约束**:
> - ✅ 只描述 WHAT（做什么）和 WHY（为什么做）
> - ❌ 不描述 HOW（怎么做）— 技术细节属于 design.md / tasks.md

## Product Decision Summary（产品决策摘要）

### Goal（用户结果）*

内容团队成员可以把“主题/文案/文章链接 + 素材链接”提交为一个知识分享短视频任务，并在 Web 端看到该任务的步骤状态与关键中间产物；失败可定位、可单步重试；产物可被 Reviewer 审查并反馈问题清单。

### Vision Link（服务愿景）*

- Vision section: Narrowest Wedge + Direction / Now + Success Signals
- Link reason: 该切片先把“从输入到可发布初稿”的生产闭环落在可追踪、可审查、可重试的任务骨架上，为后续编导/素材匹配/字幕/合成能力提供稳定承载层，并直接服务“节省 70% 制作时间”的验证路径。

### User Scenario（触发场景）*

内容团队成员要把一篇文章或一个主题快速变成知识分享短视频，但缺少短视频策划、编导与剪辑支持，需要系统先跑通“提交→产物→审核→重试”的最小闭环。

### Problem（当前问题）*

没有这套任务骨架时，团队只能通过临时脚本或手工记录推进工作：中间产物分散、步骤失败难定位、复跑成本高，Reviewer 无法基于同一套产物上下文给出可执行反馈，导致后续素材匹配与合成阶段返工。

### Proposed Options（方案建议）

| Option | Description | Pros | Cons | Recommendation |
|--------|-------------|------|------|----------------|
| A | 先做 CLI/脚本跑通任务与产物 | 实现快 | 非技术用户难用；难验证“可发现/可进入/可审阅” | no |
| B | Web 工作台 + API + Worker：任务/步骤/产物/重试骨架（最小闭环） | 可被内容团队直接使用；最符合“可审查自动化”原则 | 需要最小前后端与任务模型 | yes |
| C | 直接做完整成片流水线（含素材下载/字幕/合成） | 一步到位 | 失败面太宽，首版风险过高 | no |

### Selected Approach（选定方案）*

- Selected: Option B
- Decision reason: 先建立“可审阅产物 + 可重试”的任务骨架，再逐步增强编导、素材匹配和合成，能避免一开始把复杂度堆在不可控的媒体链路上。
- Confirmed by: user
- Confirmed at: 2026-05-05 16:44 CST

### Scope（本次范围）*

本次包括：

- 创建知识分享视频任务（输入：topic/draft/article_url + source links）
- 步骤状态（step status）与进度可查询
- 产物管理（artifact-first）：至少保存 input、LLM 原始响应或解析后 JSON（两者至少其一），以及 Reviewer findings
- 单步 retry 能力与失败留痕（保留历史产物与错误原因）
- Web 端最小可用路径：创建任务 → 查看步骤状态/产物 → 查看 Reviewer 问题清单（如有）→ 重试

### Non-goals（本次不做）*

本次不包括：

- 直接生成可发布视频初稿（字幕/封面/合成）— 原因：第一版先证明骨架与审阅闭环，避免媒体链路把失败面扩大。
- 自动全网搜索并使用素材 — 原因：版权、质量与稳定性风险高；第一版以用户提供素材为边界。
- 复杂多 Agent 编排平台 — 原因：第一版只需要编导与 Reviewer 的关键判断，其余用线性 Skill Pipeline。

### Open Questions（开放问题）

| Question | Impact | Owner | Blocking? |
|----------|--------|-------|-----------|
| 用户提供的视频链接是否可稳定下载/解析？若不可，上传素材的交互最小形态是什么？ | 影响素材路径与后续媒体步骤 | product/architect | no（本切片先定义降级路径） |

## 0. 功能分类（Feature Classification）

- `complexity_tier`: `standard`
- `implementation_mode`: `greenfield`
- `experience_surface`: `user_visible`
- `existing_implementation_note`: `N/A — greenfield feature`

---

## 1. 用户问题（User Problem）

**核心痛点**:
内容团队在缺少专业短视频运营/剪辑支持时，无法稳定推进从输入到产出的工作流；即使有生成能力，中间产物不可追踪也会导致 Reviewer 无法定位问题与返工。

**当前状态**:
用临时文档/脚本拼接流程；失败难定位；复跑不稳定；产物散落在多个工具里。

**期望状态**:
任务有可见状态与统一产物目录；任一步失败都能定位与重试；Reviewer 可基于同一上下文输出问题清单。

---

## 2. 业务目标（Business Goal）

**主要目标**:
把知识分享短视频生产抽象成“任务 + 步骤 + 产物 + 审阅 + 重试”的稳定骨架，作为后续自动化能力的承载层。

**成功指标**:
- **SI-001**: 用户能在 Web 端创建任务并看到步骤状态与产物清单。
- **SI-002**: 任一步失败都能给出可读错误原因，并能单步重试。
- **SI-003**: 任务至少产出 1 个可审阅中间产物（script/storyboard/review findings），可在 Web 或 API 中读取。

**业务价值**:
把人工从“管理混乱的生产过程”转移到“审核与小改”，为后续节省 70% 制作时间的目标提供可验证路径。

---

## 3. 用户故事（User Stories）*

### US-001 - 任务创建、产物可审阅、可重试 (Priority: P1) 🎯 MVP

**描述**:
作为 内容团队成员，我希望 提交知识分享视频任务并获得可追踪步骤状态与可审阅中间产物，以便 我只需要审核与小改，而不是从零管理整个生产过程。

**独立测试**:
可以通过 Web 创建任务，随后通过 API 查询任务状态与产物列表；模拟失败后对失败步骤 retry，确认历史产物保留且步骤可重跑。

**验收场景（Acceptance Scenarios）**:
1. **S-001 / AC-001**: **Given** 用户准备好输入与素材链接, **When** 提交任务, **Then** 系统创建任务并产出至少一个可审阅产物，且可查询步骤状态与产物清单
2. **S-002 / AC-002**: **Given** 某一步失败并记录错误原因, **When** 对该步骤 retry, **Then** 系统保留历史产物与错误上下文并重跑该步骤

---

## 3.5 验收标准（Acceptance Criteria）*

- **AC-001**: System MUST allow users to create a knowledge-share video task and retrieve step statuses and an artifact list, including at least one reviewable artifact (script/storyboard/review finding).
- **AC-002**: System MUST support retrying a failed step while preserving prior artifacts and a human-readable error reason.

---

## 4. 功能需求（Functional Requirements）*

- **FR-001**: System MUST accept task input as `topic | draft | article_url` plus `source links` and persist the normalized input for audit.
- **FR-002**: System MUST expose task status and per-step status via an API boundary that the Web UI can use.
- **FR-003**: System MUST persist step outputs as artifacts and allow listing artifacts for a task.
- **FR-004**: System MUST persist failures with an error category and a human-readable reason.
- **FR-005**: System MUST allow retrying a failed step without deleting previously generated artifacts.
- **FR-006**: System MUST record reviewer findings as structured items (stage/severity/location_ref/message/suggested_fix) when review is performed.

