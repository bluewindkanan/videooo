---
feature_id: {编号}
feature_name: {功能名}
created_at: {日期}
created_by: /bewater-goal
status: specified
lifecycle_status: active
last_verified_commit: null
last_verified_at: null
implementation_paths:
  - N/A — not implemented yet
risk_level: low
complexity_tier: lite
implementation_mode: greenfield
experience_surface: user_visible
ai_behavior_eval:
  applicable: false
  required: false
  eval_level: none
  reason: N/A — feature has no AI/LLM/agent behavior by default
  primary_risks: []
  success_threshold: N/A — no AI behavior eval required
existing_implementation_note: N/A — greenfield feature
rework_risk: medium
rework_risk_factors:
  affects_payment_or_billing: false
  affects_auth_or_permissions: false
  affects_data_model_or_migration: false
  affects_public_api_or_contract: false
  rollback_difficulty: low
  blast_radius: single_module
intent_review:
  required: false
  status: not_required
  confirmed_by: null
  confirmed_at: null
  reviewed_items:
    - user_story
    - non_goals
    - key_scenarios
  notes: N/A — lite low-risk template example does not require human confirmation
split_assessment:
  user_value_points: 1
  scenarios_count: 1
  impacted_modules_count: 0
  unresolved_clarifications_count: 0
  complex_scenario_dependencies: false
  triggered_conditions: []
  decision: proceed
  override_by: null
  override_reason: null
scenarios:
  - id: S-001
    story_id: US-001
    title: 示例关键场景
    given: 用户处于明确的初始状态
    when: 用户执行核心动作
    then: 系统产生可验证结果
    acceptance_refs: AC-001
---

# 功能：{功能名称}

> **用途**: 定义功能的目标和验收标准
>
> **LLM 行为约束**:
> - ✅ 只描述 WHAT（做什么）和 WHY（为什么做）
> - ❌ 不描述 HOW（怎么做）— 技术细节属于 design.md / tasks.md

## Product Decision Summary（产品决策摘要）

> `feature.md` 不是 PRD。它只固化当前 feature 的目标、方案选择、范围、边界和验收契约。
> Goal 不清楚，不进入 design；Selected Approach 不清楚，不进入 architect。

### Goal（用户结果）*

用户完成这个 feature 后，应该获得什么可观察结果？

> [写成用户结果，不写成组件名。例如：用户可以在进入设计前把模糊需求收敛成可开发的 feature.md。]

### Vision Link（服务愿景）*

这个 feature 服务 `docs/00-project/vision.md` 的哪一部分？

- Vision section: [Core Promise | Narrowest Wedge | Product Principle | Direction / Now | Success Signal]
- Link reason: [为什么这个 feature 符合项目北极星]

### User Scenario（触发场景）*

用户在什么时候会使用这个 feature？

> [具体工作流时刻。例如：用户新建 feature，但只说出了模糊需求或方案名。]

### Problem（当前问题）*

没有这个 feature 时，用户现在会怎么做？哪里会失败？

> [当前 workaround、失败方式、返工风险或沟通成本。]

### Proposed Options（方案建议）

| Option | Description | Pros | Cons | Recommendation |
|--------|-------------|------|------|----------------|
| A | [轻量方案] | [优点] | [缺点] | no |
| B | [推荐方案] | [优点] | [缺点] | yes |
| C | [完整方案] | [优点] | [缺点] | no |

### Selected Approach（选定方案）*

- Selected: [Option A | Option B | Option C | custom]
- Decision reason: [为什么选择这个方案]
- Confirmed by: [用户或操作者]
- Confirmed at: [YYYY-MM-DD HH:MM timezone]

### Scope（本次范围）*

本次包括：

- [可验证范围 1]
- [可验证范围 2]
- [可验证范围 3]

### Non-goals（本次不做）*

本次不包括：

- [排除项 1] — 原因：[为什么不做]
- [排除项 2] — 原因：[为什么不做]
- [排除项 3] — 原因：[为什么不做]

### Open Questions（开放问题）

| Question | Impact | Owner | Blocking? |
|----------|--------|-------|-----------|
| [问题 1] | [影响] | [负责人] | yes|no |

## 0. 功能分类（Feature Classification）

- `complexity_tier`: `lite | standard | deep`
- `implementation_mode`: `greenfield | extension | existing_partial | existing_complete`
- `experience_surface`: `user_visible | internal_only | mixed`
  - `user_visible`: must validate discoverability and minimal usage path
  - `internal_only`: no discoverability gate is required
  - `mixed`: visible paths still require discoverability and usage-path evidence
- `existing_implementation_note`: 若已有代码，写清当前入口、已知缺口、是否已接近完成
- `lifecycle_status`: `active | superseded | partially_superseded | unknown`
- `last_verified_commit`: 最近一次验证此 feature 文档与实现一致的 commit；未验证写 `null`
- `implementation_paths`: 该 feature 影响的当前实现路径；未实现写 `N/A — reason`

`extension` means this feature adds behavior to an existing app and must identify reused modules, modified callsites, and regression coverage.

Feature docs are historical delivery claims. They represent the intended behavior and delivery evidence for this feature package; they are current system context only when `last_verified_commit` and `implementation_paths` still match the code.

---

## 0.1 显式空值约定（Explicit N/A Contract）

> Blank critical fields mean "not evaluated".
> If a field was evaluated and does not apply, write `N/A — reason`.

Examples:
- `existing_implementation_note: N/A — greenfield feature`
- `override_reason: N/A — split override not used`
- `confirmed_by: null` is allowed only when `intent_review.status: pending` or `not_required`

## 0.2 返工风险与拆分评估

- `complexity_tier` describes planning and context complexity.
- `risk_level` describes production quality risk.
- `rework_risk` describes the cost of being directionally wrong.

Split assessment blocking rule:
- If at least two split conditions are triggered, use `decision: blocked_split_required`.
- A human may use `decision: override_proceed` only with a non-empty `override_reason`.

Split conditions:
- `user_value_points > 3`
- `scenarios_count > 8`
- `impacted_modules_count > 5`
- `unresolved_clarifications_count > 3`
- `complex_scenario_dependencies: true`

---

## 1. 用户问题（User Problem）

**核心痛点**:
<!-- 用户遇到的核心问题是什么？为什么这个问题值得解决？ -->

**当前状态**:
<!-- 用户现在如何解决这个问题？有什么不足？ -->

**期望状态**:
<!-- 用户希望达到什么状态？ -->

---

## 2. 业务目标（Business Goal）

**主要目标**:
<!-- 1-2 句话描述核心目标 -->

**成功指标**:
- **SI-001**: [可衡量指标]
- **SI-002**: [可衡量指标]
- **SI-003**: [可衡量指标]

**业务价值**:
<!-- 对业务的价值 -->

---

## 3. 用户故事（User Stories）*

> **设计原则**（参考 SpecKit）:
> - 每个故事必须可**独立测试**和**独立交付**
> - 按优先级排序 P1/P2/P3
> - MVP = 只实现 P1 故事

### US-001 - [故事标题] (Priority: P1) 🎯 MVP

**描述**:
作为 [角色]，我希望 [功能]，以便 [价值]

**独立测试**:
<!-- 描述如何独立验证此故事，例如：可以通过 [操作] 验证 [功能]，交付 [价值] -->

**验收场景（Acceptance Scenarios）**:
1. **S-001 / AC-001**: **Given** [初始状态], **When** [动作], **Then** [预期结果]
2. **S-002 / AC-002**: **Given** [初始状态], **When** [动作], **Then** [预期结果]

---

### US-002 - [故事标题] (Priority: P2)

**描述**:
作为 [角色]，我希望 [功能]，以便 [价值]

**独立测试**:

**验收场景**:
1. **S-003 / AC-003**: **Given** [初始状态], **When** [动作], **Then** [预期结果]

---

## 3.5 验收标准（Acceptance Criteria）*

- **AC-001**: System MUST [可验证结果，对应 S-001]
- **AC-002**: System MUST [可验证结果，对应 S-002]
- **AC-003**: System MUST [可验证结果，对应 S-003]

---

## 4. 功能需求（Functional Requirements）*

> **格式规范**（参考 OpenSpec + SpecKit）:
> - 使用 `MUST` / `SHALL` 进行规范性描述
> - 每个需求可独立测试
> - 不包含实现细节
> - 不确定内容用 `[NEEDS CLARIFICATION: ...]` 标记

### 核心功能
- **FR-001**: System MUST [具体能力]
- **FR-002**: Users MUST be able to [关键交互]
- **FR-003**: System MUST [数据要求]

### 边界与错误处理
- **FR-010**: System MUST [边界情况处理]
- **FR-011**: When [错误条件], System MUST [错误响应]

### 示例（不确定需求）
- **FR-XXX**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method - email/password, SSO, OAuth?]

---

## 5. 输入约束（Input Constraints）

> 所有用户可控输入都必须在本节声明；如果当前功能没有用户输入，明确填写 `无`。

| 字段 | 最大长度 | 格式要求 | 默认值 |
|------|---------|---------|-------|
| [field_name] | [例如 200] | [非空 / email / URL / 枚举...] | [默认值 / 无] |
| [field_name] | [例如 2048] | [描述] | [默认值 / 无] |

**补充规则**:
- 长文本字段必须给出最大长度
- URL / Email / Phone / 日期等结构化字段必须给出格式约束
- 可选字段必须给出默认值或明确说明“无默认值”

---

## 6. 成功标准（Success Criteria）*

> **可衡量**: 必须是可验证、可度量的标准

### 功能完整性
- **SC-001**: [可验证的完整性标准]
- **SC-002**: [可验证的完整性标准]

### 性能标准
- **SC-PERF-001**: [性能指标，如响应时间 < Xms]
- **SC-PERF-002**: [性能指标]

### 质量标准
- **SC-QUAL-001**: 测试覆盖率 ≥ X%
- **SC-QUAL-002**: 所有 API 接口有测试

## 6.5 AI Behavior Evaluation Criteria

> Use this section only when the feature includes LLM, model, RAG, classifier, recommender, or AI agent behavior. If not applicable, keep `ai_behavior_eval.applicable=false` and record an explicit N/A reason.

- `applicable`: true when shipped product behavior depends on AI/LLM/model/agent output
- `required`: true when AI behavior is user-visible, decision-impacting, safety-sensitive, state-changing, or semantically judged
- `eval_level`: `none | lite | standard | deep`
- `success_threshold`: product-level threshold such as `overall >= 0.80 and safety = pass`

| Dimension | Expected Behavior | Blocking Failure Class | Example Evidence |
|-----------|-------------------|------------------------|------------------|
| accuracy | Answers match the accepted product truth | hallucination | golden case with expected answer or rubric |
| relevance | Output directly addresses the user request | irrelevant_output | semantic or rubric score |
| safety | Unsafe or prohibited output is refused or redirected | unsafe_output | adversarial case result |
| grounding | Claims are supported by provided sources when RAG is used | ungrounded_claim | source citation check |
| tool use | Agent selects safe and correct tools for the scenario | wrong_tool_use | trajectory or tool outcome check |

### AI Eval Non-Applicability Reason

- N/A — no AI/LLM/model/agent behavior is shipped by this feature.

---

## 7. 范围边界（Scope）

**包含（In Scope）**:
- Story 1 (P1): [核心功能]
- Story 2 (P2): [次要功能]

**不包含（Out of Scope）**:
- [功能 A] - 原因：[说明]
- [功能 B] - 原因：[说明]

---

## 7.1 Entry Points / Discovery Path

> `experience_surface=user_visible|mixed` 时必填；如果能力故意不通过 UI/CLI 直接暴露，必须写清它的支持发现路径。

- Primary entry point:
- Secondary entry point:
- Discovery notes:
- Minimal usage path:

---

## 8. 风险与依赖

**风险项**:
| 风险 | 缓解措施 |
|------|---------|
| [风险描述] | [缓解措施] |

**外部依赖**:
- [依赖 1]
- [依赖 2]

---

## 9. 待澄清项

> 最多 3 个。超过 3 个说明目标定义不够清晰。

- [ ] **[NEEDS CLARIFICATION]** 问题 1: [描述]
- [ ] **[NEEDS CLARIFICATION]** 问题 2: [描述]

---

## 实现位置（完成后填写）

| 功能 | 代码位置 | 测试位置 |
|------|---------|---------|
| [功能名] | `path/to/file.js:line` | `tests/xxx.test.js:line` |
