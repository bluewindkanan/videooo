# Reference Map（外部参考项目映射）

> 创建日期：2026-05-05  
> 用途：在不扩大第一版范围的前提下，吸收外部开源项目的“可复用工程约束”和“可落地实现路径”。  
> 注意：这里的参考不等于技术选型结论；最终仍以 `docs/00-project/architecture.md` 的约束为准。

## 本项目第一版边界（重申）

- 视频类型：只做知识分享类短视频自动生产（口播/产品介绍仅记录扩展方向）。
- 输入：主题/文案/文章链接 + 用户提供素材链接（需要时支持上传本地素材作为替代）。
- 输出：可预览/可下载的可发布初稿；人工只做审核和小改。
- 形态：Web 工作台 + API + Worker + FFmpeg。
- 智能：编导 Agent + Reviewer Agent；其余能力以 Skill 形式实现（线性 Pipeline）。

## 外部参考项目（线上开源）

### `gyoridavid/short-video-maker`

适配点（建议吸收）：
- 把“脚本/配音/字幕/合成”做成可单独运行的步骤（step contract 明确、可重试）。
- 任务状态 + 中间产物可见（方便 Web 工作台展示、Reviewer 定位问题）。
- 接口形态（REST / 任务式提交）可作为我们首个切片的 API 参考。

对本项目的启发：
- FSC-001 不应只做 Task 记录；必须包含至少一个可审阅中间产物（如 script draft、storyboard JSON、review findings）。

### `mutonby/openshorts`

适配点（建议吸收）：
- FFmpeg 合成与字幕样式落地（工程化细节多，值得借鉴“稳定导出”的实践）。
- 平台化能力多，但第一版不要照搬其范围（避免被发布/多源素材/复杂配置拖入）。

对本项目的启发：
- 先把“合成能力”做成最小 smoke：能稳定导出一个短视频初稿，再逐步增强素材匹配质量。

### `calesthio/OpenMontage`（AGPL）

适配点（谨慎参考）：
- 复杂 agentic studio/工作流的能力清单（长期能力储备）。

不建议第一版吸收：
- 完整节点图编排、对话式编辑、通用剪辑器路线。
- 许可证约束（AGPL）对后续闭源/商用可能不友好：只做“概念参考”，不要复制代码。

### `itsjwill/vanta`

适配点（后续参考）：
- 程序化视频渲染（模板化、可控风格、可复用组件）能力的路线图。

不建议第一版吸收：
- 作为首个功能依赖（会引入渲染与模板体系的复杂度）。

## 我们要“直接落地”的工程约束（从参考项目抽出来）

### 1) Artifact-First（产物优先）

每个任务必须有 artifact 目录并可在 Web 端查看关键产物：
- 原始输入（topic/draft/url + source links）
- LLM 原始响应（便于回放与追责）
- 解析后的结构化 JSON（script/storyboard/material match）
- 音频（voiceover）
- 字幕（JSON + SRT）
- 素材片段（clips）与匹配关系（segment ↔ clip/time range）
- 封面（标题 + 图片）
- 合成日志与最终视频
- Reviewer findings（按 stage、severity、location_ref 定位）

### 2) Step Contract（步骤契约）

每个 Skill 都要具备：
- 明确输入/输出 schema（可被后续步骤消费）
- 明确产物写入位置（artifact_dir 下）
- 明确失败类型（可重试 vs 不可重试）与错误信息
- 可局部重跑（retry 单步）

### 3) Reviewability（可审查）

Reviewer Agent 输出必须是“可执行的问题清单”，不是泛泛评价：
- `stage`: script/storyboard/video
- `severity`: info/warning/blocking
- `location_ref`: script段落、storyboard segment index、视频时间窗或 clip id
- `message` + `suggested_fix`

### 4) Two Material Paths（两条素材路径）

必须支持：
- 用户提供链接（首选）
- 链接不可解析/不可下载时：用户上传本地素材作为替代

## 影响到 FSC-001 的验收点（建议）

FSC-001 不仅要“创建任务”，还要证明这条工作流能被推进与审查：
- Web 端可创建任务并看到步骤状态（至少 3 个步骤：编导/配音/合成 或 编导/审核/产物下载）。
- 任务产生至少一个可审阅产物（script draft 或 storyboard JSON 或 review findings）。
- 任务产生 artifact 目录并能列出产物清单（不要求 UI 全部展示，但 API 必须能查到）。
- 支持 retry 单步，失败时保留已生成产物和错误原因。

