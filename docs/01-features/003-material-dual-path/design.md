---
feature_id: "003"
design_version: 1.0
created_at: 2026-05-05
created_by: /bewater-architect
complexity_tier: standard
implementation_mode: extension
---

# Design: 素材两路径与失败分流（Feature 003）

## Architecture Overview

本 feature 扩展 Feature 002 的 AI 编导管线，新增 `material_fetch` 工作流步骤（排在 `script_generation` 之前），实现素材链接下载、结构化错误分类、上传替代和 `waiting_for_material` 任务暂停状态。

### 核心架构决策

| Decision | Choice | Rationale |
|----------|--------|-----------|
| HTTP 下载客户端 | httpx (sync) | 现代同步 HTTP 客户端，超时和错误处理比 requests 更精细；当前 StepRunner 为同步模式，httpx sync 与之一致 |
| 文件存储 | 扩展 ArtifactStore 支持 write_file | 复用现有 artifact 目录结构，新增二进制文件写入方法，不引入新存储抽象 |
| 下载错误分类 | 5 类枚举 + 结构化 JSON artifact | 每个链接独立处理，结果写入 material_status artifact，Web 可直接消费 |
| 上传 API | FastAPI UploadFile + multipart | 原生支持，无需额外依赖；文件校验在路由层完成 |
| Pipeline 顺序 | material_fetch 排在 script_generation 之前 | 用户已确认：素材可用性验证优先于 LLM 调用，全部失败时暂停等待上传 |
| 任务状态扩展 | 新增 waiting_for_material | 独立于 existing status 枚举，明确表达"暂停等待素材"语义 |

### Story Inventory & Scenario Coverage

| Story | Scenarios | Coverage |
|-------|-----------|----------|
| US-001 系统自动获取素材链接 | S-001 | material_fetch step + httpx download + structured status artifact |
| US-002 素材失败时任务暂停 | S-002 | waiting_for_material task status + Web failure display |
| US-003 上传替代后任务继续 | S-003 | Upload API + step completion + pipeline resume |

---

## Per-Story Technical Approach

### US-001: 系统自动获取素材链接

#### 1. material_fetch Skill

**新增文件**: `app/src/skills/material_fetch.py`

```text
class MaterialFetchResult:
    """Per-link download result."""
    url: str
    status: "success" | "failed"
    failure_category: str | None  # unreachable, unsupported_format, size_exceeded, timeout, platform_restriction
    failure_message: str | None
    storage_ref: str | None
    file_size: int | None
    content_type: str | None

def run_material_fetch(
    *,
    source_links: list[str],
    artifact_store: ArtifactStore,
    task_id: str,
) -> list[MaterialFetchResult]:
    """Download each source link, return per-link results."""
```

- 每个 URL 独立 try/except，一个失败不影响其他
- httpx 同步下载，per-request timeout 60s
- 文件类型校验：通过 Content-Type header + 扩展名双重检查
- 文件大小校验：Content-Length 预检 + 实际写入后校验
- 成功下载的文件通过 `artifact_store.write_file()` 存储
- 所有结果（含成功和失败）汇总写入 `material_status` JSON artifact

**下载错误分类规则**:

| Category | Detection |
|----------|-----------|
| `unreachable` | httpx.ConnectError, httpx.ConnectTimeout, DNS failure |
| `timeout` | httpx.ReadTimeout (连接成功但读取超时) |
| `unsupported_format` | Content-Type 不在 allowlist 或扩展名不匹配 |
| `size_exceeded` | Content-Length > MAX_FILE_SIZE 或实际写入 > MAX_FILE_SIZE |
| `platform_restriction` | HTTP 200 但 response body < 1KB 且无 Content-Type=video/* (疑似登录墙/403 页面) |

**支持的文件格式**:

```python
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi"}
ALLOWED_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}
MAX_FILE_SIZE = int(os.environ.get("VIDEOOO_MAX_MATERIAL_SIZE", 500 * 1024 * 1024))  # 500MB
DOWNLOAD_TIMEOUT = int(os.environ.get("VIDEOOO_DOWNLOAD_TIMEOUT", "60"))  # 60s
```

**测试策略**: mock httpx 调用，测试每种错误分类、格式校验和大小校验。

#### 2. ArtifactStore 扩展

**修改文件**: `app/src/artifacts/store.py`

新增 `write_file` 方法支持二进制文件存储：

```python
def write_file(
    self,
    *,
    task_id: str,
    step_key: str,
    artifact_type: str,
    filename: str,
    content: bytes,
) -> ArtifactRef:
    """Write binary file to task artifact directory."""
    # Sanitize filename: keep extension, replace name with unique
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".bin"
    name = self._unique_name(f"{step_key}-{artifact_type}", ext)
    path = self.task_dir(task_id) / name
    path.write_bytes(content)
    return ArtifactRef(storage_ref=str(path), ...)
```

- 文件名清理：保留原始扩展名，替换文件名为唯一标识
- `list_task_artifacts` 需扩展为同时列出 JSON 和二进制文件

#### 3. Domain Model 扩展

**修改文件**: `app/src/domain/models.py`

```python
# 新增 TaskStatus
class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    waiting_for_material = "waiting_for_material"  # NEW
    needs_review = "needs_review"
    failed = "failed"
    completed = "completed"

# 新增 ArtifactType
class ArtifactType(str, Enum):
    input = "input"
    llm_raw = "llm_raw"
    parsed_json = "parsed_json"
    review = "review"
    error = "error"
    source_video = "source_video"    # NEW: downloaded video
    uploaded_video = "uploaded_video" # NEW: uploaded video
    material_status = "material_status" # NEW: per-link download status
```

#### 4. StepRunner 扩展

**修改文件**: `app/src/workers/step_runner.py`

新增 `_run_material_fetch` 方法和 step 分发：

```python
STEP_SKILLS: dict[str, Callable[..., object]] = {
    "material_fetch": run_material_fetch,  # NEW
    "script_generation": run_script_generation,
    "storyboard": run_storyboard,
    "review_script": run_review_script,
}
```

material_fetch step handler 职责：
1. 从 task.source_links_json 解析 URL 列表
2. 调用 `run_material_fetch` skill
3. 写入 `material_status` artifact（JSON，含每条链接的结果）
4. 对成功下载的文件写入 `source_video` artifact
5. 判断分流：
   - 全部成功或有部分成功 → step status = completed，task status = running
   - 全部失败 → step status = failed (error_category=needs_user_action)，task status = waiting_for_material
6. 无 source_links（空列表）→ step status = completed (skipped logic)，task status = running

### US-002: 素材失败时任务暂停

#### 5. Task Status 状态机更新

**新增状态转换规则**:

```text
pending → running                    (create_video_task 开始执行 pipeline)
running → waiting_for_material       (material_fetch 全部失败)
waiting_for_material → running       (用户上传素材后)
running → needs_review               (review_script 完成)
running → failed                     (非素材步骤失败)
running → completed                  (所有步骤完成)
```

**SqliteStore 扩展**:

```python
def set_task_status(self, task_id: str, status: TaskStatus) -> None:
    """Update task status and updated_at timestamp."""
```

需要在 `create_video_task` 路由中，创建任务后立即设置 status = running。

#### 6. Web 素材状态面板

**修改文件**: `app/src/web/workbench.html`, `app/src/web/workbench.js`

任务详情页新增素材状态区域：

```text
┌─────────────────────────────────────┐
│ 素材状态                             │
├─────────────────────────────────────┤
│ https://example.com/a.mp4  ✅ 已下载 │
│ https://cdn.example.com/b.mp4 ❌ 失败 │
│   原因: 无法访问 (unreachable)       │
│                                     │
│  [上传替代素材]  ← waiting_for_material 时显示 │
└─────────────────────────────────────┘
```

- 读取 `material_status` artifact，渲染每条链接的状态
- `waiting_for_material` 状态时显示上传按钮
- 每条失败链接旁显示失败原因（中文映射）

**失败原因中文映射**:

```python
FAILURE_CATEGORY_LABELS = {
    "unreachable": "无法访问",
    "timeout": "下载超时",
    "unsupported_format": "格式不支持",
    "size_exceeded": "文件过大",
    "platform_restriction": "平台限制",
}
```

### US-003: 上传替代素材后任务自动继续

#### 7. 素材上传 API

**新增端点**: `POST /api/video-tasks/{task_id}/materials`

**修改文件**: `app/src/server/routes/video_tasks.py`

```python
@router.post("/{task_id}/materials", response_model=UploadMaterialResponse)
async def upload_material(
    req: Request,
    task_id: str,
    file: UploadFile = File(...),
) -> UploadMaterialResponse:
    """Upload a video file to replace failed source links."""
```

处理流程：
1. 校验 task 存在且 status = waiting_for_material
2. 校验文件扩展名在 allowlist 中
3. 校验 Content-Type 或扩展名
4. 校验文件大小 <= MAX_FILE_SIZE
5. 读取文件内容到内存（首版限制 500MB，内存可接受）
6. 调用 `artifact_store.write_file()` 存储
7. 写入 `uploaded_video` artifact 记录
8. 更新 material_fetch step status = completed
9. 更新 task status = running
10. 触发后续 pipeline 步骤执行（script_generation → storyboard → review_script）

**新增 Schema**:

```python
class UploadMaterialResponse(BaseModel):
    accepted: bool
    artifact_id: str | None = None
    filename: str | None = None
```

#### 8. Pipeline 触发机制

**修改文件**: `app/src/server/routes/video_tasks.py`

上传完成后需要触发后续步骤。两种方案：

- **方案 A（推荐）**: 上传路由中直接调用 StepRunner 执行后续步骤
- 方案 B: 设置 material_fetch step 为 completed，由外部调度器继续

选择方案 A，与当前 create_video_task 中直接调用 StepRunner 的模式一致。

```python
# In upload_material handler, after marking material_fetch complete:
runner = StepRunner(store=store, artifact_store=artifact_store)
for step_key in ["script_generation", "storyboard", "review_script"]:
    runner.run_step(task_id=task_id, step_key=step_key)
```

#### 9. Pipeline 顺序更新

**修改文件**: `app/src/server/routes/video_tasks.py`

```python
DEFAULT_STEP_KEYS = ["material_fetch", "script_generation", "storyboard", "review_script"]
```

创建任务后，`create_video_task` 路由中先执行 `material_fetch`：
- material_fetch 成功或部分成功 → 继续执行 script_generation → storyboard → review_script
- material_fetch 全部失败 → task status = waiting_for_material，不执行后续步骤
- 无 source_links → material_fetch 直接完成，继续后续步骤

```python
@router.post("", response_model=CreateVideoTaskResponse)
def create_video_task(req: Request, body: CreateVideoTaskRequest) -> CreateVideoTaskResponse:
    # ... create task, init steps ...
    runner = StepRunner(store=store, artifact_store=artifact_store)

    # Run material_fetch first
    runner.run_step(task_id=task.id, step_key="material_fetch")

    # Check if material_fetch blocked the pipeline
    task = store.get_task(task.id)
    if task and task.status != TaskStatus.waiting_for_material:
        # Continue pipeline
        for step_key in ["script_generation", "storyboard", "review_script"]:
            runner.run_step(task_id=task.id, step_key=step_key)

    return CreateVideoTaskResponse(task_id=task.id)
```

---

## Shared Cross-Story Concerns

### Security

| Concern | Mitigation |
|---------|------------|
| 上传恶意文件 | 扩展名白名单 + Content-Type 校验 + 不执行上传文件 |
| 路径遍历攻击 | filename 清理：只保留扩展名，替换为 UUID |
| 超大文件攻击 | Content-Length 预检 + 实际写入大小限制 |
| SSRF (下载内网地址) | 首版不限制（内部工具）；后续可加 IP 黑名单 |

### Error Handling

| Error Category | When | Behavior |
|----------------|------|----------|
| `unreachable` | DNS/network error | 记录到 material_status，该链接标记 failed |
| `timeout` | 下载超过 60s | 记录到 material_status，该链接标记 failed |
| `unsupported_format` | Content-Type 或扩展名不在白名单 | 记录到 material_status，该链接标记 failed |
| `size_exceeded` | 文件 > 500MB | 记录到 material_status，该链接标记 failed |
| `platform_restriction` | 疑似登录墙/403 页面 | 记录到 material_status，该链接标记 failed |
| `upload_invalid_task` | 上传到非 waiting_for_material 任务 | 返回 409 Conflict |
| `upload_invalid_file` | 扩展名/大小不合规 | 返回 422 Unprocessable Entity |

### Schema Validation

上传文件校验：
1. 扩展名在 `ALLOWED_EXTENSIONS` 中（.mp4, .mov, .avi）
2. Content-Type 在 `ALLOWED_CONTENT_TYPES` 中（video/mp4, video/quicktime, video/x-msvideo）
3. 文件大小 <= `MAX_FILE_SIZE`（默认 500MB）

---

## Data Model Changes

### TaskStatus 新增枚举值

```python
class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    waiting_for_material = "waiting_for_material"  # NEW
    needs_review = "needs_review"
    failed = "failed"
    completed = "completed"
```

### ArtifactType 新增枚举值

```python
class ArtifactType(str, Enum):
    input = "input"
    llm_raw = "llm_raw"
    parsed_json = "parsed_json"
    review = "review"
    error = "error"
    source_video = "source_video"     # NEW
    uploaded_video = "uploaded_video"  # NEW
    material_status = "material_status" # NEW
```

### SqliteStore 新增方法

```python
def set_task_status(self, task_id: str, status: TaskStatus) -> None:
    """Update task status and updated_at."""

def update_task_status(self, task_id: str, status: TaskStatus) -> None:
    """Alias for set_task_status; also updates updated_at."""
```

---

## API Changes

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/video-tasks/{task_id}/materials | 上传素材文件（multipart/form-data） |

### Modified Endpoints

| Method | Path | Change |
|--------|------|---------|
| POST | /api/video-tasks | DEFAULT_STEP_KEYS 增加 material_fetch；pipeline 触发逻辑更新 |

---

## E2E Test Strategy

| Scenario | Required | Driver | Coverage | Test Asset Path | Data/Auth Setup | Artifact Policy |
|----------|----------|--------|----------|-----------------|-----------------|-----------------|
| S-001 | integration | API integration test | Mock httpx，验证下载状态 artifact 写入 | `app/tests/integration/test_api_video_tasks.py` | 无 auth，内存 DB | 保留 |
| S-002 | integration | API integration test | 验证全部失败 → waiting_for_material 状态 | 同上 | 同上 | 保留 |
| S-003 | integration | API integration test | 上传文件 → task 恢复 running | 同上 | 同上 | 保留 |

首版不做 Playwright E2E。Web 验证通过 API integration + blackbox smoke 覆盖。

blackbox smoke: `app/tests/blackbox/video_task_smoke.sh` 需更新，包含 source_links 场景。

---

## AI Behavior Evaluation Strategy

### AI Eval Non-Applicability

- `applicable`: false
- `reason`: 素材获取和上传是确定性文件操作（HTTP 下载 + multipart 上传 + 文件存储），不涉及 AI/LLM/Agent 行为。

N/A — no AI/LLM/model/agent behavior is shipped by this feature.

---

## Constitution Notes

| Principle | Compliance | Notes |
|-----------|-----------|-------|
| P1: Evidence-First Delivery | ✅ | material_fetch 有独立单元测试，上传 API 有集成测试，下载错误分类有覆盖 |
| P2: User-Visible Slice First | ✅ | 用户可观察每个素材的获取状态和失败原因，可上传替代 |
| P3: Simplicity Over Speculation | ✅ | 使用 httpx 同步客户端（不引入 Celery/异步队列），文件存储复用现有 ArtifactStore |
| P4: Use Existing Architecture | ✅ | 复用 FastAPI/SQLite/ArtifactStore 架构，新增方法和枚举值，不引入新框架 |
| P5: Boundary Validation | ✅ | API 集成测试覆盖下载/上传/状态转换完整链路 |
| P6: Workflow Over Editor | ✅ | 素材管理服务于 pipeline 流程，不做素材编辑器 |
| P7: Reviewable Automation | ✅ | material_status artifact 保留每条链接的完整下载历史和失败原因 |
| P8: Rights-Aware Inputs | ✅ | Web 保持素材权利声明；上传功能不改版权责任边界 |
| P9: Artifact-First | ✅ | 素材文件和下载状态都写入可追踪 artifact |

No constitutional conflicts.

---

## Entry Points / Discovery Path

- Primary entry point: Web 工作台任务详情页，素材状态面板自动展示
- Secondary entry point: API `POST /api/video-tasks/{task_id}/materials`，上传素材文件
- Discovery notes: 用户创建带 source_links 的任务后，material_fetch 步骤自动执行；失败时 Web 显示上传入口
- Minimal usage path: 创建任务（带链接）→ 查看素材状态 → 失败时上传 → 任务继续

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| httpx 未安装 | low | low | 添加到 requirements.txt |
| 大文件下载占用内存 | medium | medium | httpx 流式下载，写入临时文件 |
| 素材平台反爬 | high | high | 结构化错误分类 + 上传替代路径 |
| 上传文件安全风险 | medium | low | 扩展名白名单 + 大小限制 + filename 清理 |
| waiting_for_material 无超时 | low | low | 首版不设超时，用户可随时上传或放弃 |

---

## ADR (Architecture Decision Records)

### ADR-003-1: 使用 httpx 同步客户端下载素材

- **Context**: 需要下载用户提供的素材链接，当前 StepRunner 为同步模式。
- **Decision**: 使用 httpx 同步客户端，per-request timeout 60s。
- **Consequence**: 与现有同步 StepRunner 一致，无需引入异步。后续如改为异步 Worker 可平滑迁移。
- **Alternatives**: requests → 不支持 HTTP/2，超时处理不如 httpx；aiohttp → 需要异步架构改造。

### ADR-003-2: 扩展 ArtifactStore 而非引入新存储层

- **Context**: 当前 ArtifactStore 只支持 JSON 文件，素材需要存储二进制文件。
- **Decision**: 新增 `write_file` 方法到现有 ArtifactStore，复用 task 目录结构。
- **Consequence**: 保持存储层统一，artifact 管理逻辑集中。文件命名规则统一。
- **Alternatives**: 独立 MaterialStore → 额外抽象层，违反 P3；对象存储(S3/MinIO) → 内部工具不需要。

### ADR-003-3: material_fetch 排在 script_generation 之前

- **Context**: 素材获取和 LLM 编导是独立的，可并行或串行。
- **Decision**: material_fetch 排在 pipeline 最前面，全部失败时阻塞后续步骤。
- **Consequence**: 用户能在消耗 LLM tokens 前知道素材是否可用；但如果部分成功也会等待下载完成。
- **Alternatives**: material_fetch 排在 review_script 之后 → 素材不可用时不阻塞 LLM 调用，但浪费 tokens。

### ADR-003-4: 上传路由直接触发后续 pipeline

- **Context**: 上传完成后需要继续执行后续步骤。
- **Decision**: 在上传路由中直接调用 StepRunner 执行后续步骤，与 create_video_task 模式一致。
- **Consequence**: 实现简单，与现有架构一致。后续可改为异步调度。
- **Alternatives**: 消息队列 → 过度设计；定时轮询 → 延迟高。
