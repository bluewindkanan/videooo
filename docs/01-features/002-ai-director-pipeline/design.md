---
feature_id: "002"
design_version: 1.0
created_at: 2026-05-05
created_by: /bewater-architect
complexity_tier: standard
implementation_mode: extension
---

# Design: AI 编导管线（Feature 002）

## Architecture Overview

本 feature 扩展 Feature 001 的任务骨架，将占位符 StepRunner 替换为真实 LLM 调用，新增 storyboard 步骤，并升级 Web 工作台为可用级。

### 核心架构决策

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM 调用方式 | Skill adapter + OpenAI-compatible protocol | 国产模型（通义千问/智谱 GLM）大多兼容 OpenAI API 格式，用一套 adapter 即可切换供应商 |
| 首版 LLM 供应商 | 通义千问（Qwen） | 中文质量好、API 稳定、OpenAI-compatible、成本低 |
| StepRunner 拆分 | 每个 step_key 对应一个 Skill 函数 | 替代当前 if/elif 分发，支持独立测试和扩展 |
| Web 技术方案 | 单页 HTML + vanilla JS | 与 Feature 001 一致，不引入前端框架，保持简单 |
| 任务列表实现 | 新增 GET /api/video-tasks 端点 | 现有 API 只有单任务查询，需要列表端点支持 Web 任务列表 |
| 产物内容获取 | 新增 GET /api/video-tasks/{id}/artifacts/{artifact_id}/content | Web 需要读取 artifact JSON 内容来渲染可读展示 |

### Story Inventory & Scenario Coverage

| Story | Scenarios | Coverage |
|-------|-----------|----------|
| US-001 AI 生成文案/分镜并展示结果 | S-001, S-002, S-003 | Skill adapter + LLM prompt + Web rendering |
| US-002 任务列表与导航 | S-004 | API list endpoint + Web task list page |

---

## Per-Story Technical Approach

### US-001: AI 生成文案/分镜并展示结果

#### 1. LLM Skill Adapter

**新增文件**: `app/src/skills/llm_adapter.py`

```text
class LLMAdapter:
    """LLM 调用适配器，隔离供应商差异。"""

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None: ...
    def chat(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str: ...
```

- 使用 OpenAI-compatible HTTP API（`/v1/chat/completions`）
- 通过环境变量 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 配置
- 首版默认值指向通义千问 DashScope endpoint
- adapter 不做 JSON 解析，只返回 raw text，由调用方负责解析

**测试策略**: mock HTTP 调用，验证 request 格式和 error handling。

#### 2. Skill 实现

**新增目录**: `app/src/skills/`

每个 Skill 是一个纯函数，接收输入、调用 LLM、返回结构化输出：

```text
app/src/skills/
├── __init__.py
├── llm_adapter.py          # LLM 调用适配器
├── script_generation.py    # 文案生成 skill
├── storyboard.py           # 分镜生成 skill
└── review_script.py        # 审查 skill
```

**script_generation.py**:

- Input: `input_kind`, `input_text`
- LLM prompt: system prompt 定义输出 JSON schema（hook/body/call_to_action/estimated_duration_seconds）
- Output: `ScriptDraft` dict
- Error: parse 失败时保存 raw response，标记 `parse_error`

**storyboard.py**:

- Input: `ScriptDraft`（从上一个 step 的 artifact 读取）
- LLM prompt: 基于文案生成 3-8 个分镜段，每段包含 voiceover_text/visual_intent/expected_keywords/estimated_start_seconds/estimated_end_seconds
- Output: `list[StoryboardSegment]`
- 新增步骤 key: `storyboard`

**review_script.py**:

- Input: `ScriptDraft` + `list[StoryboardSegment]`（从 artifact 读取）
- LLM prompt: 审查文案和分镜的质量，输出结构化 findings
- Output: `list[ReviewFinding]`（每条含 stage/severity/location_ref/message/suggested_fix）

每个 Skill 必须同时写入两个 artifact：
1. `llm_raw` — LLM 原始响应文本
2. `parsed_json` — 解析后的结构化 JSON

#### 3. StepRunner 重构

**修改文件**: `app/src/workers/step_runner.py`

将当前的 if/elif 分发改为 skill dispatch：

```python
STEP_SKILLS: dict[str, Callable] = {
    "script_generation": run_script_generation,
    "storyboard": run_storyboard,
    "review_script": run_review_script,
}
```

StepRunner.run_step 的职责简化为：
1. 设置 step status = running
2. 查找对应 skill 函数
3. 调用 skill 函数
4. 写入 artifact
5. 设置 step status = completed 或 failed

保留现有的线程锁和 FAIL 注入逻辑（用于 smoke test）。

#### 4. 步骤顺序更新

**修改文件**: `app/src/server/routes/video_tasks.py`

```python
DEFAULT_STEP_KEYS = ["script_generation", "storyboard", "review_script"]
```

创建任务后依次执行所有步骤（当前是同步执行，后续 feature 可改为异步）。

#### 5. 产物内容 API

**新增端点**: `GET /api/video-tasks/{task_id}/artifacts/{artifact_id}/content`

- 读取 artifact 的 storage_ref（文件路径），返回 JSON 内容
- Web 前端通过此端点获取 artifact 数据来渲染可读展示

### US-002: 任务列表与导航

#### 6. 任务列表 API

**新增端点**: `GET /api/video-tasks`

- 返回所有任务列表（按创建时间倒序）
- 包含 task_id, status, input_kind, input_text (truncated), created_at
- 新增 `TaskListItemDTO` 和 `TaskListResponse` schema

**新增方法**: `SqliteStore.list_tasks()`

#### 7. Web 工作台升级

**修改文件**: `app/src/web/workbench.html`, `app/src/web/workbench.js`

采用单页模式，通过 hash routing 实现页面切换：

```text
#/                → 任务列表页（默认）
#/task/{id}       → 任务详情页
#/new             → 创建任务页
```

**任务列表页**:
- 卡片列表，每张卡片显示：任务 ID（缩写）、状态 badge、输入摘要、创建时间
- 点击卡片跳转到详情页
- 顶部"创建新任务"按钮

**任务详情页**:
- 任务基本信息卡片（输入内容、状态、时间）
- 步骤状态卡片（横向或纵向排列，每步显示状态 badge + 进度 + 错误信息）
- 产物展示区：
  - script: 可读的文案卡片（hook 标题、body 正文、CTA、预估时长）
  - storyboard: 分镜表格（序号/旁白/画面意图/关键词/时段）
  - review: 问题清单（severity badge + 位置 + 内容 + 建议）
- 失败步骤的重试按钮

**样式**: 使用纯 CSS，保持与 Feature 001 一致的简洁风格。不引入 CSS 框架。

---

## Shared Cross-Story Concerns

### Error Handling

| Error Category | When | Behavior |
|----------------|------|----------|
| `rate_limit` | LLM API 返回 429 | 保存错误，step status = failed，支持重试 |
| `api_error` | LLM API 返回 5xx 或网络错误 | 保存错误，step status = failed，支持重试 |
| `parse_error` | LLM 输出无法解析为预期 JSON | 保存 raw response 为 llm_raw artifact，step status = failed |
| `content_filter` | LLM 拒绝生成（内容安全） | 保存错误，step status = failed，error_category = non_retryable |

### Schema Validation

每个 Skill 的 LLM prompt 必须在 system prompt 中声明输出 JSON schema。解析时使用 Pydantic model 校验：

- `ScriptDraftSchema`: hook (str), body (str), call_to_action (str), estimated_duration_seconds (int)
- `StoryboardSegmentSchema`: segment_index (int), voiceover_text (str), visual_intent (str), expected_keywords (list[str]), estimated_start_seconds (float), estimated_end_seconds (float)
- `ReviewFindingSchema`: stage (str), severity (str), location_ref (str), message (str), suggested_fix (str)

校验失败时走 `parse_error` 路径。

### LLM Prompt Design Principles

- System prompt 必须包含输出 JSON schema 定义
- User prompt 包含具体输入（topic/draft/article_url + 素材链接）
- Storyboard prompt 必须包含完整文案内容
- Review prompt 必须包含完整文案和分镜内容
- 所有 prompt 必须要求 JSON-only 输出（no markdown wrapping）

---

## Data Model Changes

### 新增 ArtifactType 枚举值

```python
class ArtifactType(str, Enum):
    input = "input"
    llm_raw = "llm_raw"        # already exists
    parsed_json = "parsed_json"  # already exists
    review = "review"           # already exists
    error = "error"             # already exists
    # No new types needed for this feature
```

当前 `ArtifactType` 枚举已覆盖所需类型，无需修改。

### SqliteStore 新增方法

```python
def list_tasks(self) -> list[VideoTask]:
    """Return all tasks ordered by created_at DESC."""
```

---

## API Changes

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/video-tasks | 列出所有视频任务 |
| GET | /api/video-tasks/{task_id}/artifacts/{artifact_id}/content | 获取产物 JSON 内容 |

### Modified Endpoints

| Method | Path | Change |
|--------|------|---------|
| POST | /api/video-tasks | DEFAULT_STEP_KEYS 增加 storyboard |

---

## E2E Test Strategy

| Scenario | Required | Driver | Coverage | Test Asset Path | Data/Auth Setup | Artifact Policy |
|----------|----------|--------|----------|-----------------|-----------------|-----------------|
| S-001 | blackbox_smoke | API integration test | Mock LLM，验证 artifact 写入和 schema | `app/tests/integration/test_api_video_tasks.py` | 无 auth，内存 DB | 保留 |
| S-002 | blackbox_smoke | API integration test | Mock LLM，验证分镜 artifact | 同上 | 同上 | 保留 |
| S-003 | blackbox_smoke | API integration test | Mock LLM，验证 findings 结构 | 同上 | 同上 | 保留 |
| S-004 | blackbox_smoke | API integration test | 创建多任务后验证列表 | 同上 | 同上 | 保留 |

首版不做 Playwright E2E。Web 验证通过 API integration + blackbox smoke 覆盖。blackbox_smoke via `app/tests/blackbox/video_task_smoke.sh`。

---

## AI Behavior Evaluation Strategy

### Eval Dimensions & Scenarios

| Dimension | Scenario | Eval Type | Dataset Path | Scorer/Rubric | Threshold |
|-----------|----------|-----------|-------------|---------------|-----------|
| accuracy | S-001: 文案与主题语义相关 | golden + rubric | `app/evals/002/golden.jsonl` | 自动 schema 合规 + 人工 rubric 打分 | schema合规 >= 0.9 |
| relevance | S-002: 分镜与文案对应 | golden + rubric | 同上 | 每段分镜有对应文案区间 | >= 0.85 |
| safety | S-003: Reviewer 发现有害内容 | adversarial | 同上 | Reviewer 必须标记 | blocking |
| format | All: JSON schema 合规 | automated | 同上 | Pydantic schema 校验 | 100% |
| grounding | S-003: findings 引用实际位置 | golden | 同上 | location_ref 指向真实内容 | >= 0.8 |

### Eval Command

```bash
python3 app/evals/run_002.py
```

### Result Artifact

`app/eval-results/002.json`

### Eval Level: standard

标准级评估：golden cases + adversarial cases + rubric scoring。不做自动化回归流水线，但要求 eval 可一键运行。

---

## Constitution Notes

| Principle | Compliance | Notes |
|-----------|-----------|-------|
| P1: Evidence-First Delivery | ✅ | 每个 Skill 有独立单元测试，API 有集成测试，AI 行为有 eval |
| P2: User-Visible Slice First | ✅ | 本 feature 直接交付用户可观察的 AI 编导结果和可用 Web 工作台 |
| P3: Simplicity Over Speculation | ✅ | LLM adapter 只做当前需要的 chat 调用，不预建 embedding/RAG 等能力 |
| P4: Use Existing Architecture | ✅ | 复用 Feature 001 的 FastAPI/SQLite/Artifact 架构，不引入新框架 |
| P5: Boundary Validation | ✅ | API 集成测试 + blackbox smoke + AI eval 覆盖边界 |
| P6: Workflow Over Editor | ✅ | Web 只做可读展示，不做编辑器 |
| P7: Reviewable Automation | ✅ | 每个 Skill 保留 llm_raw + parsed_json 双产物 |
| P8: Rights-Aware Inputs | ✅ | Web 保持素材权利声明 |
| P9: Artifact-First | ✅ | 每步都写入可追踪 artifact |

No constitutional conflicts.

---

## Entry Points / Discovery Path

- Primary entry point: `GET /workbench` → 任务列表页
- Secondary entry point: `POST /api/video-tasks` → API 直接创建
- Discovery: 打开 `/workbench` 即可看到任务列表 + 创建按钮
- Minimal usage path: `/workbench` → 点击"创建新任务" → 输入主题 → 提交 → 查看文案/分镜/Review

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| LLM JSON 输出不稳定 | medium | medium | Pydantic schema 校验 + raw response 保留 + prompt engineering |
| 通义千问 API 不可用 | high | low | adapter 模式支持切换，测试 mock 不依赖真实 API |
| Web 工作台范围蔓延 | medium | medium | 严格限制为可读展示，不做编辑 |
| 并发创建任务时 LLM 调用冲突 | low | low | 保留 Feature 001 的线程锁机制 |

---

## ADR (Architecture Decision Records)

### ADR-002-1: LLM Adapter 使用 OpenAI-compatible protocol

- **Context**: 需要支持多个国产 LLM 供应商，且能在测试中 mock。
- **Decision**: LLM adapter 使用 OpenAI-compatible chat completions API 作为标准接口。
- **Consequence**: 通义千问、智谱 GLM、DeepSeek 等都支持此协议，切换成本低。测试通过 mock HTTP 请求实现。
- **Alternatives**: 直接用各厂商 SDK → 供应商绑定，切换成本高。

### ADR-002-2: Skill 作为纯函数，不使用 Agent 框架

- **Context**: Feature 001 已有线性 StepRunner，且 Constitution P3 要求简约优于猜测。
- **Decision**: 每个 Skill 实现为纯函数（input → LLM call → output），不走复杂 Agent 框架。
- **Consequence**: 实现简单、可测试、可独立运行。后续如需 Agent 能力（如工具调用），在 Skill 内部封装。
- **Alternatives**: LangChain/LangGraph Agent → 过度设计，违反 P3。

### ADR-002-3: Web 工作台继续使用 vanilla HTML/JS

- **Context**: 当前工作台是 HTML + vanilla JS。引入 React/Vue 会增加复杂度和构建步骤。
- **Decision**: 继续使用 vanilla HTML/JS + hash routing，不引入前端框架。
- **Consequence**: 保持简单，不引入构建工具链。当工作台复杂度显著增加时再考虑框架。
- **Alternatives**: React SPA → 需要构建工具链，对当前规模过重。
