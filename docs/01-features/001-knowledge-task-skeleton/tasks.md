# Tasks: 001-knowledge-task-skeleton

---
feature_id: "001"
feature_name: 知识分享视频任务骨架（任务 / 步骤 / 产物）
created_at: 2026-05-05
created_by: /bewater-plan
status: planned_draft
complexity_tier: standard
implementation_mode: greenfield
experience_surface: user_visible
sources:
  feature: docs/01-features/001-knowledge-task-skeleton/feature.md
  design: docs/01-features/001-knowledge-task-skeleton/design.md
---

## Build Plan（给 PM / 业务方看的实现摘要）

我们将交付一个 **可在 Web 工作台中创建“知识分享视频任务”** 的最小闭环，并满足两类用户可见能力：

1) **任务 / 步骤 / 产物可见**：创建任务后，可在任务详情中看到步骤状态与产物清单，且至少产出 1 个可审阅产物（script / storyboard / review findings 三者其一即可）。  
2) **失败留痕 + 单步重试**：任一步失败都能展示可读错误原因；用户可对失败步骤点击 retry，系统保留历史产物与错误上下文并重新执行。

为避免首版把不确定性堆到素材下载/解析上，第一版会把“source links 不可下载/不可解析”记录为 **需要用户动作** 的失败类型，并在 UI 上提示降级为“上传素材”（先做提示与错误分类；上传本身可作为后续任务或最小占位实现）。

**证明它可用的证据**：
- API 边界 smoke：`POST create -> GET status -> GET artifacts -> POST retry`（S-001/S-002）。  
- Lite AI 行为评估：为编导/Reviewer 的结构化输出建立 `golden.jsonl + rubric`，跑通 `schema_check + 最小质量阈值`（design.md 的 AI Behavior Evaluation Strategy）。

主要风险 / 会导致 build 停下来的原因：
- 任务/步骤状态机与 artifact 目录策略未收敛（会导致不可审阅、不可重试）。
- 黑盒 smoke 或 eval 资产无法稳定复现（无法进入 validate/ship）。

相关文档：`tasks.md`（本文件）与 `prebuild-review.md`（收敛审查）。

---

## Task Overview（SSOT for readiness / receipts）

| Task | Status | Depends on | Type | Receipt |
|---|---|---|---|---|
| T001 | done | - | implementation | receipts.json#T001 |
| T002 | done | T001 | implementation | receipts.json#T002 |
| T003 | done | T002 | implementation | receipts.json#T003 |
| T004 | done | T003 | implementation | receipts.json#T004 |
| T005 | done | T004 | implementation | receipts.json#T005 |
| T006 | done | T004,T005 | implementation | receipts.json#T006 |
| T007 | done | T004,T005 | implementation | receipts.json#T007 |
| T008 | done | T001 | implementation | receipts.json#T008 |

> Note: “Status” must match each task’s `task_readiness` field below.

---

## Source Contract（Story/Scenario → Design/Test 映射）

| story_id | scenario_id | AC refs | Design coverage (from design.md) | Planned proof |
|---|---|---|---|---|
| US-001 | S-001 | AC-001 | Web + API + Worker + ArtifactStore | blackbox_smoke（API）+ lite eval |
| US-001 | S-002 | AC-002 | StepRunner + RetryPolicy + Artifact retention | blackbox_smoke（API）+ unit（retry/state） |

---

## Testing Asset Map（required by design.md）

> 目标：首版以 `blackbox_smoke` 覆盖用户可见边界；`static_verify` 仅作补充，不可替代。

| scenario_id | Level | Driver | Test asset path | RED command | Verify command | Artifacts / receipts |
|---|---|---|---|---|---|---|
| S-001 | blackbox_smoke | API (`curl`) | `app/tests/blackbox/video_task_smoke.sh` | `bash app/tests/blackbox/video_task_smoke.sh` | `curl -sS http://127.0.0.1:8000/api/video-tasks`（脚本内应包含等价调用） | `docs/01-features/001-knowledge-task-skeleton/receipts.json#T007` |
| S-002 | blackbox_smoke | API (`curl`) | `app/tests/blackbox/video_task_retry_smoke.sh` | `bash app/tests/blackbox/video_task_retry_smoke.sh` | `curl -sS http://127.0.0.1:8000/api/video-tasks/{id}/retry`（脚本内应包含等价调用） | `docs/01-features/001-knowledge-task-skeleton/receipts.json#T007` |

---

## Eval Asset Map（required: ai_behavior_eval.required=true）

| scenario_id | eval type | dataset path | rubric/scorer | Eval RED command | Verify command | Result artifact | receipts ref |
|---|---|---|---|---|---|---|---|
| S-001 | tool_outcome + schema_check | `app/evals/001/golden.jsonl` | `app/evals/001/rubric.md` | `python -m app.evals.run_001` | `python -m app.evals.run_001 --verify` | `app/eval-results/001.json` | `docs/01-features/001-knowledge-task-skeleton/receipts.json#T008.eval_evidence` |
| S-002 | tool_outcome | `app/evals/001/golden.jsonl` | deterministic | `python -m app.evals.run_001 --retry` | `python -m app.evals.run_001 --retry --verify` | `app/eval-results/001.json` | `docs/01-features/001-knowledge-task-skeleton/receipts.json#T008.eval_evidence` |

---

## Task List（含依赖、风险、测试映射、readiness）

### T001: Application skeleton + tooling bootstrap（FastAPI + pytest）
- story/scenario refs: US-001 / S-001, S-002（支撑所有实现）
- acceptance refs: AC-001, AC-002
- scope:
  - 建立 `app/` 下可运行的 Python 应用骨架（与 `python -m app...` 保持一致）
  - 引入测试框架（pytest）与基础 CI 命令（lint 可后置）
- planned files (exact in-scope):
  - `app/__init__.py`
  - `app/src/server/__init__.py`
  - `app/src/server/main.py`（FastAPI app）
  - `app/src/domain/`（占位包）
  - `app/tests/`（pytest 目录骨架）
  - `app/pyproject.toml`（或等价依赖管理；以 repo 现状为准）
- tests:
  - static_verify: `python -m compileall app`（或 `python -m ruff` 若引入）
  - unit: `pytest -q`（先跑通空集/样例）
- dependencies: none
- risks:
  - Python package/layout 与 `app/src/...` 的一致性（避免后续 import 路径混乱）
- task_readiness: `done`（receipt: `docs/01-features/001-knowledge-task-skeleton/receipts.json#T001`）

### T002: Data model + persistence（VideoTask / WorkflowStep / TaskArtifact）
- story/scenario refs: US-001 / S-001, S-002
- acceptance refs: AC-001, AC-002
- scope:
  - 定义核心模型与状态枚举（task/step/artifact）
  - 选择最小持久化：首版推荐 SQLite（单机）+ 文件系统 artifact_dir
  - 提供 repository 层接口，便于后续替换
- tests:
  - unit: 状态机转换、retry_count、artifact retention 规则
- test mapping: unit（`app/tests/unit/test_models.py`）
- dependencies: T001
- risks:
  - 过度抽象（违反 Simplicity Over Speculation）
- task_readiness: `done`（receipt: `docs/01-features/001-knowledge-task-skeleton/receipts.json#T002`）

#### Execution Block (T002)

- **Story / scenario refs**: Story=US-001; Scenarios=S-001,S-002; Acceptance=AC-001,AC-002
- **Design refs**:
  - `docs/01-features/001-knowledge-task-skeleton/design.md`（数据模型章节）
  - `docs/00-project/architecture.md`（目录约束）
- **Exact files in scope**:
  - `app/src/domain/__init__.py`
  - `app/src/domain/models.py`（或 `video_task.py` 等；以保持单文件最小为优先）
  - `app/src/storage/__init__.py`
  - `app/src/storage/sqlite.py`
  - `app/tests/unit/test_models.py`
- **Callsites / reuse checklist**:
  - N/A（greenfield；无既有调用点需要盘点）
- **RED command**:
  - `pytest -q app/tests/unit/test_models.py`
- **Expected RED failure marker**:
  - `ModuleNotFoundError` 或断言失败（枚举/字段未定义）
- **GREEN target**:
  - 模型与存储最小实现可创建/读取 task、steps、artifacts；测试通过
- **Verify commands**:
  - `python -m compileall app`
  - `pytest -q`
- **Receipt path**:
  - `docs/01-features/001-knowledge-task-skeleton/receipts.json#T002`
- **Done definition**:
  - `VideoTask / WorkflowStep / TaskArtifact`（含 status 枚举与时间字段）在 domain 层可导入
  - SQLite repo 层可在单进程下完成：create task + init steps + append artifact + list artifacts
  - 不引入“未来可能需要”的抽象（保持最小）
- **Escalation notes**:
  - 若发现必须引入非 SQLite / 非文件系统 artifact 才能完成最小闭环：先停下并回到 plan 重新评估（避免在 build 阶段漂移设计）。

### T003: ArtifactStore（artifact-first + failure retention）
- story/scenario refs: US-001 / S-001, S-002
- acceptance refs: AC-001, AC-002
- scope:
  - 每个 task 建立 artifact_dir
  - 写入：normalized input、llm_raw（或 parsed_json）、review findings（如有）
  - 失败时写入 error artifact（含 category + human-readable reason）
  - 产物索引：API 可列出 artifacts（metadata）
- tests:
  - unit: artifact 写入/列表、失败不删除旧产物
- test mapping: unit（`app/tests/unit/test_artifacts.py`）
- dependencies: T002
- risks:
  - 产物命名/metadata 不稳定导致 UI/验证脚本脆弱
- task_readiness: `done`（receipt: `docs/01-features/001-knowledge-task-skeleton/receipts.json#T003`）

#### Execution Block (T003)

- **Story / scenario refs**: Story=US-001; Scenarios=S-001,S-002; Acceptance=AC-001,AC-002
- **Design refs**: `docs/01-features/001-knowledge-task-skeleton/design.md`（ArtifactStore / 风险章节）
- **Exact files in scope**:
  - `app/src/artifacts/__init__.py`
  - `app/src/artifacts/store.py`
  - `app/tests/unit/test_artifacts.py`
- **Callsites / reuse checklist**:
  - N/A（greenfield）
- **RED command**:
  - `pytest -q app/tests/unit/test_artifacts.py`
- **Expected RED failure marker**:
  - 断言失败（未保留历史产物 / metadata 缺失）
- **GREEN target**:
  - artifact 写入、列表、失败留痕、历史保留的单测通过
- **Verify commands**:
  - `pytest -q`
- **Receipt path**:
  - `docs/01-features/001-knowledge-task-skeleton/receipts.json#T003`
- **Done definition**:
  - 每个 task 有稳定 `artifact_dir` 规则
  - 同一 step 多次 attempt 产物不互相覆盖（保留历史）
- **Escalation notes**:
  - 若 artifact 命名/metadata 无法稳定：以 “最小可审计 JSON 索引 + 明确字段” 优先，避免先做复杂 UI。

### T004: API endpoints（create/status/artifacts/retry）
- story/scenario refs: US-001 / S-001, S-002
- acceptance refs: AC-001, AC-002
- scope:
  - 实现 design.md 的 4 个端点：
    - `POST /api/video-tasks`
    - `GET /api/video-tasks/:id`
    - `GET /api/video-tasks/:id/artifacts`
    - `POST /api/video-tasks/:id/retry`
  - 返回结构满足 Web 与 smoke 脚本消费
- tests:
  - integration: FastAPI TestClient 跑 create→status→artifacts
- test mapping: integration（`app/tests/integration/test_api_video_tasks.py`）
- dependencies: T003
- risks:
  - API 返回与 smoke/eval 资产不一致（导致证据链断裂）
- task_readiness: `done`（receipt: `docs/01-features/001-knowledge-task-skeleton/receipts.json#T004`）

#### Execution Block (T004)

- **Story / scenario refs**: US-001 / S-001, S-002（AC-001, AC-002）
- **Design refs**: `docs/01-features/001-knowledge-task-skeleton/design.md`（API 设计章节）
- **Exact files in scope**:
  - `app/src/server/main.py`
  - `app/src/server/routes/video_tasks.py`
  - `app/src/server/schemas.py`
  - `app/tests/integration/test_api_video_tasks.py`
- **Callsites / reuse checklist**:
  - N/A（greenfield）
- **RED command**:
  - `pytest -q app/tests/integration/test_api_video_tasks.py`
- **Expected RED failure marker**:
  - `404 Not Found`（路由未注册）或响应 schema 不匹配
- **GREEN target**:
  - 4 个端点按契约返回（含 steps 与 artifacts 列表）；集成测试通过
- **Verify commands**:
  - `pytest -q`
- **Receipt path**:
  - `docs/01-features/001-knowledge-task-skeleton/receipts.json#T004`
- **Done definition**:
  - `POST /api/video-tasks` 返回 task_id，并初始化 steps
  - `GET /api/video-tasks/:id` 返回 task + steps（含状态）
  - `GET /api/video-tasks/:id/artifacts` 返回 artifacts metadata 列表
  - `POST /api/video-tasks/:id/retry` 可接受 step_key（仅允许 failed step）
- **Escalation notes**:
  - 若 API schema 无法同时满足 smoke 脚本与未来 UI：以 smoke + spec 收敛为准，UI 可后置调整但不得破坏契约。

### T005: StepRunner + Worker loop（线性 step + retry 互斥）
- story/scenario refs: US-001 / S-001, S-002
- acceptance refs: AC-001, AC-002
- scope:
  - 线性 step：至少包含一个“可审阅产物生成”步骤（例如 `script_generation` 或 `review_script`）
  - 幂等/互斥：同一 `task_id + step_key` 同时只能运行一个 attempt
  - retry policy：仅允许 `failed` step；保留历史 artifacts
  - failure 分类：`needs_user_action` / `transient` / `non_retryable`
- tests:
  - unit: 互斥与 retry rules
  - integration: API 触发 step 并观察状态变化
- dependencies: T004
- risks:
  - 并发/幂等缺失导致状态错乱（validate 无法通过）
- test mapping: unit（`app/tests/unit/test_step_runner.py`）+ integration（复用 `app/tests/integration/test_api_video_tasks.py` 扩展）
- task_readiness: `done`（receipt: `docs/01-features/001-knowledge-task-skeleton/receipts.json#T005`）

#### Execution Block (T005)

- **Story / scenario refs**: Story=US-001; Scenario=S-001,S-002; Acceptance=AC-001,AC-002
- **Design refs**: `docs/01-features/001-knowledge-task-skeleton/design.md`（StepRunner + RetryPolicy + 风险章节）
- **Exact files in scope**:
  - `app/src/workers/__init__.py`
  - `app/src/workers/step_runner.py`
  - `app/src/storage/sqlite.py`（补充 step 状态更新/失败留痕）
  - `app/src/server/routes/video_tasks.py`（create 触发 step，retry 触发重跑）
  - `app/tests/unit/test_step_runner.py`
  - `app/tests/integration/test_api_video_tasks.py`
- **Callsites / reuse checklist**:
  - N/A（greenfield）
- **RED command**:
  - `pytest -q app/tests/unit/test_step_runner.py`
- **Expected RED failure marker**:
  - `ERROR: file or directory not found: app/tests/unit/test_step_runner.py` 或断言失败（step 未写入可审阅 artifact / retry 不生效）
- **GREEN target**:
  - step 运行后：对应 step 状态从 pending → completed（或 failed），并写入至少 1 个可审阅 artifact（例如 `parsed_json` 的脚本草稿占位）
  - retry 仅允许 failed step；保留历史 artifacts（artifact retention 在 store/命名上体现）
- **Verify commands**:
  - `python -m pytest -q`
- **Receipt path**:
  - `docs/01-features/001-knowledge-task-skeleton/receipts.json#T005`
- **Done definition**:
  - create task 后能异步/同步执行至少一个 step 并生成可审阅产物（script/storyboard/review finding 其一）
  - step 失败时写入 error_category + human-readable error_message，且 retry 可重置并重新执行
  - 同一 task_id + step_key 并发触发时不会同时运行两个 attempt（最小互斥）
- **Escalation notes**:
  - 若 FastAPI BackgroundTasks/线程池导致状态不稳定：先以“同步执行 + 黑盒脚本稳定”为优先，后续再异步化。

### T006: Web workbench minimal UI（discoverability + minimal usage path）
- story/scenario refs: US-001 / S-001, S-002
- acceptance refs: AC-001, AC-002
- scope:
  - 页面：任务列表/创建入口（可先直接进入创建页）、任务详情（steps + artifacts + reviewer findings）
  - 失败展示：错误原因 + retry 按钮
  - 权利边界提示：用户对输入素材负责（Rights-Aware Inputs）
  - 素材降级提示：link 不可用时提示上传素材（可只做提示与错误分类）
- tests:
  - black-box smoke（可选）：后续升级到 Playwright；首版可先靠 API smoke + 手工验证证据（validate 阶段补齐）
- dependencies: T004 + T005
- risks:
  - UI 不可发现/路径不完整（违反 User-Visible Slice First）
- test mapping: manual_smoke（打开 `/workbench`，创建任务并查看 artifacts / retry）
- task_readiness: `done`（receipt: `docs/01-features/001-knowledge-task-skeleton/receipts.json#T006`）

#### Execution Block (T006)

- **Story / scenario refs**: Story=US-001; Scenario=S-001,S-002; Acceptance=AC-001,AC-002
- **Design refs**: `docs/01-features/001-knowledge-task-skeleton/design.md`（Entry Points & Discovery Path）
- **Exact files in scope**:
  - `app/src/server/main.py`（挂载静态页 / 路由）
  - `app/src/web/workbench.html`
  - `app/src/web/workbench.js`
- **Callsites / reuse checklist**:
  - N/A（greenfield）
- **RED command**:
  - `curl -sS http://127.0.0.1:8000/workbench | head`
- **Expected RED failure marker**:
  - `404 Not Found`
- **GREEN target**:
  - `/workbench` 可访问，并可通过页面调用 API 完成：创建任务 → 查看 steps/artifacts → 失败 step retry
- **Verify commands**:
  - `python3 -m uvicorn app.src.server.main:app --host 127.0.0.1 --port 8000 & sleep 1; curl -sS http://127.0.0.1:8000/workbench | head -n 5`
- **Receipt path**:
  - `docs/01-features/001-knowledge-task-skeleton/receipts.json#T006`
- **Done definition**:
  - 工作台页面可发现（至少 1 个入口），并展示最小使用路径信息（steps/artifacts/retry）
  - 页面含“素材权利边界”提示与“链接失败→上传素材（后续）”提示文案
- **Escalation notes**:
  - 若引入前端构建链路会显著增重：首切片保持纯静态 HTML/JS。

### T007: Blackbox smoke scripts（S-001/S-002）
- story/scenario refs: US-001 / S-001, S-002
- acceptance refs: AC-001, AC-002
- scope:
  - 按 design.md 的建议路径写入两条可运行脚本
  - 脚本输出应包含可审计 JSON（task/steps/artifacts）
- tests:
  - blackbox_smoke: `bash app/tests/blackbox/video_task_smoke.sh`
  - blackbox_smoke: `bash app/tests/blackbox/video_task_retry_smoke.sh`
- test mapping: blackbox_smoke（`app/tests/blackbox/video_task_smoke.sh`, `app/tests/blackbox/video_task_retry_smoke.sh`）
- dependencies: T004 + T005（必要），T006（非必须）
- risks:
  - 脚本对环境/端口依赖不明确导致不可复现
- task_readiness: `done`（receipt: `docs/01-features/001-knowledge-task-skeleton/receipts.json#T007`）

#### Execution Block (T007)

- **Story / scenario refs**: Story=US-001; Scenario=S-001,S-002; Acceptance=AC-001,AC-002
- **Design refs**: `docs/01-features/001-knowledge-task-skeleton/design.md`（E2E Test Strategy）
- **Exact files in scope**:
  - `app/tests/blackbox/video_task_smoke.sh`
  - `app/tests/blackbox/video_task_retry_smoke.sh`
  - `app/tests/blackbox/_common.sh`（如需要）
- **Callsites / reuse checklist**:
  - N/A（greenfield）
- **Test level**: blackbox_smoke
- **E2E asset**:
  - Driver: `curl` + shell
  - Scenario coverage: S-001 / S-002
  - Smoke command: `bash app/tests/blackbox/video_task_smoke.sh`（内部包含 `curl .../api/video-tasks` 等调用）
- **E2E runtime**:
  - Server: `uvicorn app.src.server.main:app --host 127.0.0.1 --port 8000`
  - Base URL: `http://127.0.0.1:8000`
  - Data/auth setup: N/A（首切片无鉴权；SQLite + 本地 artifacts）
- **Evidence artifacts**:
  - stdout/stderr command log（CI 输出或本地终端输出）
  - JSON 响应体（脚本打印）
- **RED command**:
  - `bash app/tests/blackbox/video_task_smoke.sh`
- **Expected RED failure marker**:
  - `curl: (7) Failed to connect` 或 `HTTP/1.1 404`
- **GREEN target**:
  - 两个脚本均能输出可审计 JSON（task/steps/artifacts），并以 0 退出
- **Verify commands**:
  - `bash app/tests/blackbox/video_task_smoke.sh`
  - `bash app/tests/blackbox/video_task_retry_smoke.sh`
- **Receipt path**:
  - `docs/01-features/001-knowledge-task-skeleton/receipts.json#T007`
- **Done definition**:
  - 脚本自包含：明确服务启动方式（例如要求先运行 `uvicorn ...`）与 base_url（默认 `http://127.0.0.1:8000`）
  - 输出包含：task_id、steps（含 status）、artifacts（至少 1 个可审阅产物或其占位 artifact）
- **Escalation notes**:
  - 若黑盒脚本依赖过多外部状态：先把依赖收敛为 “启动命令 + base_url + SQLite 路径 + artifact_dir”，不得引入额外手工步骤。

### T008: AI behavior eval assets + runner（lite）
- story/scenario refs: US-001 / S-001, S-002
- acceptance refs: AC-001, AC-002（以“可审阅产物结构与最小质量”支撑）
- scope:
  - `app/evals/001/golden.jsonl`：最小数据集（topic/draft/article_url + 期望输出形态）
  - `app/evals/001/rubric.md`：最小质量阈值（跑题/事实疑点/结构缺失）
  - `app/evals/run_001.py`：执行 schema_check + 质量打分（lite）
  - `app/eval-results/001.json`：输出结果（可覆盖 retry 场景）
- tests:
  - unit: rubric/scorer 的确定性（同输入稳定输出）
- dependencies: T001（独立于 API/Worker，可并行推进）
- risks:
  - eval 变成“主观点评”而非可审计规则（validate 难以复核）
- test mapping: eval_runner（`python -m app.evals.run_001 --verify`）
- task_readiness: `done`（receipt: `docs/01-features/001-knowledge-task-skeleton/receipts.json#T008`）

#### Execution Block (T008)

- **Story / scenario refs**: Story=US-001; Scenario=S-001,S-002; Acceptance=AC-001,AC-002
- **Design refs**: `docs/01-features/001-knowledge-task-skeleton/design.md`（AI Behavior Evaluation Strategy）
- **Exact files in scope**:
  - `app/evals/001/golden.jsonl`
  - `app/evals/001/rubric.md`
  - `app/evals/__init__.py`
  - `app/evals/run_001.py`
  - `app/eval-results/001.json`
  - `app/tests/unit/test_eval_run_001.py`（可选，但建议）
- **Callsites / reuse checklist**:
  - N/A（greenfield）
- **RED command**:
  - `python -m app.evals.run_001 --verify`
- **Expected RED failure marker**:
  - `ModuleNotFoundError: No module named 'app.evals.run_001'` 或 verify 阈值失败
- **GREEN target**:
  - `python -m app.evals.run_001 --verify` 以 0 退出，并写出 `app/eval-results/001.json`
- **Verify commands**:
  - `python -m app.evals.run_001 --verify`
  - `python -m app.evals.run_001 --retry --verify`
- **Receipt path**:
  - `docs/01-features/001-knowledge-task-skeleton/receipts.json#T008`
- **Done definition**:
  - dataset + rubric + runner + result artifact 齐全（可审计）
  - runner 为 deterministic（同输入稳定输出），且阈值可解释
- **Escalation notes**:
  - 若 eval 需要真实 LLM 调用：本切片不引入外部 LLM 成本；先以 deterministic placeholder + schema/quality rule 作为 lite 轨道落地。

---

## Execution Block（next dispatchable ready batch）

> 当前 ready 批次：T008（AI behavior eval assets）。其余任务保持 backlog。

---

## Execution Block（next dispatchable ready batch）

> 目标：让 Builder 进入 build 时，不需要再补“该改哪些文件、怎么跑 RED、怎么验证”的细节。

### Batch A（建议先执行）：T001

- **Story / scenario refs**: US-001 / S-001, S-002（AC-001, AC-002）
- **Design refs**:
  - `docs/01-features/001-knowledge-task-skeleton/design.md`：API / 模型 / eval strategy
  - `docs/00-project/architecture.md`：目录约束（`app/src/...`）
- **Exact files in scope**:
  - `app/__init__.py`
  - `app/src/server/__init__.py`
  - `app/src/server/main.py`
  - `app/tests/__init__.py`（如需要）
  - `app/tests/unit/test_sanity.py`（或等价）
  - `app/pyproject.toml`
- **Callsites / reuse checklist**:
  - N/A（greenfield）
- **RED command**:
  - `pytest -q`
- **Expected RED failure marker**:
  - `ERROR: file or directory not found: app/tests` 或 `ModuleNotFoundError: No module named 'app'`
- **GREEN target**:
  - `pytest -q` 通过（至少 1 个 sanity test）
- **Verify commands**:
  - `python -m compileall app`
  - `pytest -q`
- **Receipt path**:
  - `docs/01-features/001-knowledge-task-skeleton/receipts.json#T001`
- **Done definition**:
  - 能 `python -c "import app"` 成功
  - `pytest -q` 通过
  - `app/src/server/main.py` 暴露可被后续任务挂载的 FastAPI app（即使暂时无业务路由）
- **Escalation notes**:
  - 若发现 repo 计划使用 Node/TS 而非 Python：不得私自改 design.md；应在 build 入口前通过 review-note 触发方法论内的 drift 处理（本切片以 design.md 为 SSOT）。

---

## Constitution Compliance Notes（required）

- Evidence-First Delivery：计划中包含 blackbox smoke 与 eval 资产；每个关键能力都有可运行命令与 receipts 绑定（T007/T008）。
- User-Visible Slice First：T006 明确 UI 最小可用路径；API/Worker 的实现以 UI 可消费为目标，而非纯底座。
- Simplicity Over Speculation：首版不引入通用编排引擎；StepRunner 线性、最小步骤。
- Boundary Validation：S-001/S-002 均有 black-box smoke；unit/integration 仅为补充。
- Reviewable Automation + Artifact-First：T003 将 artifact 作为一等对象；失败留痕与历史保留写入计划。
- Rights-Aware Inputs：T006 包含素材权利边界提示与下载失败降级提示。
