# Architecture（架构约束）

> BeWater 项目级全局架构文档 | 创建日期：2026-05-05
> 适用于整个视频自动化生产平台。应用代码位于 `app/`，以下代码路径均以仓库根目录表示，并与 `.bewater/install-meta.json` 的 `application_root=app` 对齐。

## 架构概览

**架构风格**：Web 应用 + API 服务 + 后台媒体生产流水线。

**核心原则**：
- 线性 Pipeline 优先，不做复杂多 Agent 编排。
- Agent 只承担需要判断、审阅、反复推理的职责；纯执行能力封装为 Skill。
- 视频类型通过工作流配置扩展，共享媒体处理能力。
- 第一版服务内部内容团队，优先可运行和可验证，不为未来外部平台过度抽象。

## 技术栈约束

### 前端

- 形态：Web 工作台。
- 责任：提交视频生产任务、展示步骤状态、预览 Reviewer 问题、预览和下载成片。
- 路径：`app/src/web/...`。
- 性能指标：面向 Web 的用户体验指标使用 LCP、CLS、INP；不使用已废弃的首次输入延迟指标。

### 后端

- 形态：API 服务 + 任务队列 + Worker。
- 责任：任务创建、状态管理、Skill 调用、媒体处理调度、产物存储。
- 路径：`app/src/server/...`、`app/src/workers/...`。
- 媒体处理：服务端 FFmpeg 负责下载后的切片、字幕烧录或外挂字幕、音画合成、封面合成和最终导出。

### AI 与外部服务

- LLM：用于编导 Agent、Reviewer Agent、文案生成、分镜生成、质量审查。
- TTS：外部 API 优先，用于配音生成。
- 视频下载和素材解析：服务端能力，第一版只处理用户提供链接或用户上传素材。
- 供应商必须通过 Skill 接口隔离，避免业务流程直接依赖某个 API 的专有字段。

### 数据与存储

- 数据库保存任务、输入源、步骤状态、文案、分镜、素材片段、Reviewer 问题和输出索引。
- 文件存储保存原始素材、下载片段、音频、字幕、封面和成片。
- 任务步骤必须记录错误原因和可重试状态。


## Resources Reference Review（参考项目实践吸收）

初始化后复核了 `resources/` 下的视频相关项目，结论是：本项目不能照搬通用剪辑器或复杂 Agent 视频编辑器，但应吸收它们在任务状态、产物管理、审核和媒体处理上的成熟约束。

### 参考项目与可用经验

- `resources/MoneyPrinterTurbo`：验证了短视频自动生成可以采用线性流程：script → terms/materials → audio → subtitle → materials → compose；其中 `stop_at` 风格的阶段性输出值得吸收，用于先验证文案、配音、字幕、素材等中间结果。
- `resources/autoclip`：验证了长任务必须有 Project/Task 数据模型、步骤目录、元数据文件、数据库同步、路径管理和 WebSocket/轮询进度；本项目需要从第一版就把中间产物作为一等对象管理。
- `resources/FireRed-OpenStoryline` / `resources/ai-video-editor`：验证了节点化视频工作流和 Skill 加载机制有价值，但其完整 node map 和对话式编辑能力对第一版过重；本项目只吸收 typed node/skill contract，不照搬复杂多 Agent 编排。
- `resources/videocut-skills`：验证了口播剪辑和字幕流程必须保留人工审核界面、字/句级时间戳、专业词典、用户习惯规则和“只改不加”的审核原则；这些对 Reviewer Agent 和字幕节点有直接参考价值。
- `resources/remotion`：验证了 React 程序化视频渲染可作为后续封面、字幕样式和模板化视频的候选方案；第一版仍以 FFmpeg 为基线，避免过早引入渲染框架和许可证/部署复杂度。
- `resources/OpenCut`：验证了通用编辑器会把范围拉向时间线、特效、导出和多端能力；本项目明确不沿这个方向做第一版。

### 吸收为架构约束

1. 每个视频任务必须有独立 artifact directory，保存输入、LLM 原始响应、解析后 JSON、音频、字幕、素材片段、封面、合成视频和 Reviewer findings。
2. 每个 Skill 必须支持阶段性输出和失败重试；用户应能看到当前步骤、错误原因和已有中间产物。
3. Reviewer Agent 不是泛泛打分器，必须输出带 `stage`、`severity`、`location_ref`、`message`、`suggested_fix` 的可执行问题。
4. 字幕和音画匹配必须以时间戳为核心数据结构；后续如果先剪辑再加字幕，字幕必须基于剪辑后视频，而不是原始素材。
5. 第一版素材策略应支持“用户提供链接”和“用户上传本地素材”两条路径；链接下载失败时不能阻塞整个产品方向，必须给出上传替代。
6. 渲染层第一版使用 FFmpeg；Remotion/React 渲染只作为后续模板化视频和复杂视觉样式候选，不作为首个功能依赖。

## 模块划分

```text
app/src/web/                 Web 工作台
app/src/server/              API、认证、任务查询和提交
app/src/domain/              VideoTask、Workflow、SkillContract 等领域对象
app/src/workflows/           视频类型工作流定义
app/src/agents/              编导 Agent、Reviewer Agent
app/src/skills/              可复用 Skill 实现
app/src/media/               FFmpeg、素材下载、字幕、封面、合成
app/src/artifacts/           任务产物目录、元数据、LLM 原始响应和中间文件管理
app/src/storage/             数据库和文件存储适配
app/tests/                   单元、集成、边界和媒体 smoke 测试
```

## 视频类型工作流边界

**Video Type Workflow = Agent Role + Skill Pipeline + Shared Media Runtime**。

第一版知识分享工作流：

1. 用户提交主题、文案或链接，并提供素材链接。
2. 编导 Agent 调用 `script_generation_skill` 生成短视频文案。
3. 编导 Agent 调用 `storyboard_skill` 输出分镜意图和画面匹配提示。
4. Reviewer Agent 调用 `review_script_skill` 检查文案和分镜。
5. 系统调用 `voiceover_skill` 生成配音。
6. 系统调用 `material_extract_skill` 从用户提供链接提取素材片段。
7. 系统调用 `material_match_skill` 将旁白片段匹配到素材片段。
8. 系统调用 `subtitle_skill` 生成字幕。
9. 系统调用 `cover_skill` 生成封面标题和封面图。
10. 系统调用 `video_compose_skill` 合成视频初稿。
11. Reviewer Agent 调用 `review_video_skill` 检查成片、字幕、画面匹配和明显错误。
12. Web 端展示视频初稿、Reviewer 问题和下载入口。

后续口播工作流复用字幕、封面、合成和 Reviewer 能力，但输入改为口播原片。后续产品介绍工作流复用编导、配音、字幕、封面和合成能力，但素材策略需要单独设计。

## Agent 与 Skill 约束

### Agent

- 编导 Agent：负责创作判断，包括选题理解、短视频文案、结构、分镜意图和封面方向。
- Reviewer Agent：负责质量审查，包括文案跑题、事实疑点、表达问题、字幕错误、素材匹配问题和成片可发布性。

### Skill

Skill 是可复用能力包，必须有稳定输入、输出、错误状态、artifact 写入位置和测试边界。每个 Skill 的输出应可被后续步骤直接消费，也应可在 Web 端被用户或 Reviewer 查看。第一版候选 Skills：

- `script_generation_skill`
- `storyboard_skill`
- `voiceover_skill`
- `material_extract_skill`
- `material_match_skill`
- `subtitle_skill`
- `cover_skill`
- `video_compose_skill`
- `review_script_skill`
- `review_video_skill`

禁止把所有步骤做成相互对话的 Agent 网络。只有当一个能力确实需要独立目标、工具调用、反复推理和审查状态时，才升级为 Agent。

## 数据模型

### VideoTask

```text
id: string
video_type: knowledge_share | talking_head | product_intro
status: pending | running | needs_review | failed | completed
input_kind: topic | draft | article_url
input_text: string
source_links: SourceLink[]
current_step: string
created_at: timestamp
updated_at: timestamp
```

### WorkflowStep

```text
task_id: string
step_key: string
status: pending | running | failed | completed | skipped
progress_percent: integer
input_ref: string
output_ref: string
artifact_dir: string
error_message: string
retry_count: integer
started_at: timestamp
completed_at: timestamp
```

### TaskArtifact

```text
id: string
task_id: string
step_key: string
artifact_type: input | llm_raw | parsed_json | audio | subtitle | source_video | clip | cover | final_video | review
storage_ref: string
metadata: object
created_at: timestamp
```


### ScriptDraft

```text
task_id: string
version: integer
hook: string
body: string
call_to_action: string
estimated_duration_seconds: integer
review_status: unchecked | passed | flagged
```

### StoryboardSegment

```text
task_id: string
segment_index: integer
voiceover_text: string
visual_intent: string
expected_keywords: string[]
estimated_start_seconds: number
estimated_end_seconds: number
matched_material_ref: string
```

### MediaAsset

```text
id: string
task_id: string
source_link_id: string
asset_type: source_video | uploaded_video | clip | voiceover | subtitle | cover | final_video
storage_ref: string
start_seconds: number
end_seconds: number
metadata: object
```


### ReviewFinding

```text
task_id: string
stage: script | storyboard | video
severity: info | warning | blocking
location_ref: string
message: string
suggested_fix: string
```

## API 设计约束

第一版 API 至少覆盖：

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/video-tasks | 创建视频生产任务 |
| GET | /api/video-tasks/:id | 查看任务状态和步骤结果 |
| POST | /api/video-tasks/:id/retry | 重试失败步骤 |
| GET | /api/video-tasks/:id/artifacts | 获取任务中间产物列表 |
| GET | /api/video-tasks/:id/preview | 获取预览信息 |
| GET | /api/video-tasks/:id/download | 下载最终视频 |

具体框架在第一个 feature 的 design 阶段确定。初始化阶段只规定边界，不锁死实现。

## 关键约束

### 性能约束

- Web 任务页面应能快速显示已知状态，媒体生产耗时通过后台任务处理，不阻塞请求；进度更新可用 WebSocket 或轮询实现，首版不强制复杂实时通道。
- 单条知识分享短视频生成时间应明显低于人工制作时间，第一版以节省 70% 制作时间为目标。
- 媒体处理步骤必须可观测，用户能看到当前步骤和失败原因。

### 安全约束

- 用户输入文本、链接和生成内容都必须按不可信数据处理。
- Web 输出必须防 XSS：不直接渲染未净化 HTML；Markdown 或富文本必须走安全白名单。
- 外链、iframe 和第三方脚本必须有明确 allowlist；默认不嵌入未知第三方脚本。
- 第一版不承诺自动版权判断；必须在产品边界中声明用户负责输入素材使用权。
- 若后续加入认证，授权模型至少要保证任务和素材只能被创建者或授权团队访问。
- 建议配置 CSP，限制脚本来源、媒体来源和 frame 来源。

### 可扩展性约束

- 新视频类型应优先定义新的 Workflow 配置和少量专用 Skill，而不是复制整套媒体处理逻辑。
- LLM、TTS、素材下载和存储供应商必须通过适配层隔离。
- Skill contract 变更必须同步更新测试和相关 Workflow。

### 可维护性约束

- 不在第一版实现复杂通用编排引擎。
- 每个 Skill 必须能独立测试，至少覆盖成功、失败和边界输入。
- 用户可见行为必须有边界级验证：API、Web smoke、Worker 集成或媒体合成 smoke。
- AI 行为必须有评估样例，覆盖文案质量、素材匹配和 Reviewer 发现能力。

## 风险与处理

- 素材链接不可下载：提供明确失败原因，并支持用户上传本地素材作为替代路径。
- 文案质量不稳定：Reviewer Agent 标记问题，允许用户重新生成或人工修改。
- 素材匹配不准：ReviewFinding 必须定位到片段，便于人工小改。
- 外部 API 成本或延迟过高：通过 Skill adapter 替换供应商或降级。
- FFmpeg 合成失败：保留中间产物和日志，支持从失败步骤重试。
