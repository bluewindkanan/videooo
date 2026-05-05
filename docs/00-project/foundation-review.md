# Foundation Review（项目基础评审）

> 生成日期：2026-05-05
> 生成命令：/bewater-init
> 评审对象：docs/00-project/vision.md、architecture.md、constitution.md、decision-log.md

## Review Summary

项目基础已足够进入第一个功能目标阶段。北极星明确：不是通用剪辑器，而是面向内部内容团队的知识分享短视频自动化生产工作流。第一版范围收敛到主题、文案或链接加素材链接，生成可预览和下载的可发布初稿。架构约束明确采用 Web 应用、后台媒体生产流水线、编导 Agent、Reviewer Agent 和 Skill Pipeline，不做复杂多 Agent 编排。

## Foundation Gate Checks

| 检查项 | 结果 | 说明 |
|--------|------|------|
| North star clarity | passed | 核心用户、问题、承诺和最小切口明确。 |
| Architecture constraints coherence | passed | Web、API、Worker、FFmpeg、Agent 与 Skill 边界一致。 |
| Constitution completeness | passed | 默认 BeWater 原则和视频平台特有原则已确认。 |
| Decision-log cleanup | passed | 决策记录只保留当前项目决策，无模板示例。 |
| Unfilled content removal | passed | 项目层文档无待填写内容。 |
| Application root path alignment | passed | 架构文档明确应用代码位于 `app/` 并使用 `app/src/...` 路径。 |
| Project document consistency | passed | vision、architecture、constitution 和 decisions 对第一版范围一致。 |

## Reference Practice Review

复核 `resources/` 后，基础方向保持不变，但首个功能候选需要更强调工程骨架中的 artifact 管理和可审阅中间产物：

- MoneyPrinterTurbo 支持线性脚本到视频流程和阶段性 `stop_at` 输出，说明第一版可以先让每个步骤有可见产物。
- AutoClip 的项目目录、步骤元数据、任务状态和路径管理说明视频系统不能只存最终视频。
- OpenStoryline 的 node/skill schema 说明 typed contract 有价值，但完整节点图和对话式编辑对第一版过重。
- videocut-skills 的审核网页、字级时间戳、词典和“只改不加”规则说明 Reviewer 与字幕必须可定位、可人工确认。
- Remotion 可作为后续程序化渲染候选；OpenCut 明确提醒不要走通用剪辑器路线。

因此 FSC-001 的含义从“任务创建骨架”收紧为“任务 + 步骤 + artifact + 最小可审阅产物”的生产骨架。

## Key Risks

1. 素材链接不可下载或平台限制解析。
2. 用户提供素材的版权和授权边界需要产品提示明确。
3. 素材匹配质量是第一版核心技术风险，必须可定位到片段并允许人工小改。
4. LLM 和 TTS API 的成本、延迟和稳定性会影响内部使用体验。
5. 如果过早做复杂 Agent 编排或通用剪辑能力，会稀释最小闭环。

## First Slice Candidates

### FSC-001：知识分享视频任务创建、步骤状态与 Artifact 骨架

- **source_basis**：vision.md Narrowest Wedge、Target User、Core Promise、Success Signals。
- **user_value**：内容团队可以在 Web 端提交主题、文案或链接和素材链接，看到一个视频生产任务被创建，并能追踪编导、素材、字幕、封面、合成等步骤状态和关键中间产物。
- **why_this_should_be_first**：这是从输入到成片闭环的入口、状态和产物骨架，后续所有 Skill、Agent、Reviewer 和媒体处理能力都依赖它。
- **risk_note**：如果只做任务骨架而无用户可见产物，价值不足；该切片必须至少包含一个真实可审阅中间产物，例如编导文案草稿、分镜 JSON 或 Reviewer finding。并且需要明确“最小可验收点”，避免后续在素材/字幕/合成阶段返工。
- **acceptance (建议写入 /bewater-goal)**：
  - Web 端可创建任务并查看步骤状态（至少覆盖：编导产物、Reviewer 产物、媒体合成其中的任意 2 个环节）。
  - 任务产生至少 1 个可审阅产物（script draft 或 storyboard JSON 或 review findings），并能在 Web 或 API 中被读取。
  - 任务有 artifact 目录（或等价存储索引），并能列出产物清单（至少包含：input、llm_raw/parsed_json 二选一）。
  - 支持 retry 单步；失败时保留已生成产物和可读错误原因。
  - 明确素材路径的降级策略：链接不可解析时支持上传本地素材（不要求此切片实现完整下载器，但必须给出产品路径）。
- **recommended**：true

### FSC-002：编导 Agent 生成知识分享短视频文案和分镜

- **source_basis**：vision.md Core Problem、Product Principles、Direction Now。
- **user_value**：用户输入主题、文案或链接后，得到可审核的短视频文案和分镜意图，减少从零策划和写稿时间。
- **why_this_should_be_first**：编导能力是替代短视频策划的核心，且比完整媒体合成更容易验证。
- **risk_note**：如果单独交付，不能证明从脚本到成片的完整承诺；需要与任务骨架或后续合成切片衔接。
- **recommended**：false

### FSC-003：最小素材匹配与合成 smoke

- **source_basis**：vision.md Current Alternative、Core Promise、architecture.md 视频类型工作流边界。
- **user_value**：用户提供一段素材链接和短文案，系统生成配音、字幕并合成为一个短视频 smoke 初稿。
- **why_this_should_be_first**：直接验证最难的语义素材匹配和 FFmpeg 合成链路。
- **risk_note**：如果没有编导输出，输入可能过于人工化；如果媒体解析失败，切片容易被外部平台限制阻断。
- **recommended**：false

## Recommended First Slice

推荐首个功能候选：**FSC-001：知识分享视频任务创建、步骤状态与 Artifact 骨架**。

推荐理由：该切片建立用户入口、任务状态、工作流步骤、artifact 管理和可扩展边界，是后续编导 Agent、Reviewer Agent、Skill Pipeline 和媒体处理的共同承载层。为了保持用户价值，进入 `/bewater-goal` 时应要求它包含至少一个最小真实生成结果，例如编导文案草稿、分镜 JSON 或 Reviewer finding，而不是纯后台框架。

## Human Confirmation Required

进入 `/bewater-goal` 前，需要用户确认是否以 FSC-001 作为第一个功能目标。也可以选择 FSC-002 或 FSC-003，但必须重新明确首个 feature 的用户可见价值和验证边界。
