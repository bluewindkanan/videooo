# Decision Log（决策记录）

> 记录关键技术决策和架构选择，确保决策可追溯。

## 决策清单

| 编号 | 标题 | 日期 | 状态 | 决策者 |
|------|------|------|------|--------|
| D001 | 第一版聚焦知识分享类短视频自动生产 | 2026-05-05 | 已采纳 | 项目创建者 |
| D002 | 采用 Web 应用 + 后台媒体生产流水线 | 2026-05-05 | 已采纳 | 项目创建者 |
| D003 | 使用编导 Agent、Reviewer Agent 与 Skill Pipeline，而不是复杂多 Agent 编排 | 2026-05-05 | 已采纳 | 项目创建者 |
| D004 | 第一版直接使用用户提供链接素材，版权判断由用户负责 | 2026-05-05 | 已采纳 | 项目创建者 |
| D005 | 吸收参考项目实践：任务产物、步骤状态、审核界面和 Skill contract 优先 | 2026-05-05 | 已采纳 | 项目创建者 |
| D006 | Per-segment TTS with edge-tts word boundary timing | 2026-05-05 | 已采纳 | Architect |
| D007 | edge-tts timing for subtitles (no Whisper) | 2026-05-05 | 已采纳 | Architect |
| D008 | Fixed-duration clip extraction + sequential duration-based matching | 2026-05-05 | 已采纳 | Architect |
| D009 | FFmpeg concat demuxer for video composition | 2026-05-05 | 已采纳 | Architect |
| D010 | No source videos → solid color fallback | 2026-05-05 | 已采纳 | Architect |

---

### D001：第一版聚焦知识分享类短视频自动生产

**日期**：2026-05-05  
**状态**：已采纳  
**决策者**：项目创建者

**背景**：项目长期希望支持知识分享、口播和产品介绍三类短视频，但初始化阶段需要选择最小可验证切口。

**选项**：
1. 同时设计三类视频工作流。优点是覆盖完整愿景；缺点是范围过大，难以验证核心价值。
2. 先聚焦知识分享工作流。优点是输入、流程和成功标准最清楚；缺点是口播和产品介绍需要后续扩展。

**决策**：先聚焦知识分享类短视频自动生产。

**后果**：第一版围绕主题、文案或链接到可发布初稿的闭环推进；口播和产品介绍只作为架构扩展方向记录。

**验证**：内容团队能生成可预览和下载的视频初稿，并相比人工流程节省至少 70% 制作时间。

---

### D002：采用 Web 应用 + 后台媒体生产流水线

**日期**：2026-05-05  
**状态**：已采纳  
**决策者**：项目创建者

**背景**：内容团队需要提交输入、查看进度、预览问题和下载结果，视频生成本身是耗时任务。

**选项**：
1. 内部 CLI 或脚本。优点是最快跑通；缺点是非技术用户使用门槛高。
2. Web 应用。优点是适合内容团队提交和审核；缺点是需要实现基本界面和任务状态。
3. 桌面工具。优点是本地媒体处理可控；缺点是分发和协作成本较高。

**决策**：采用 Web 应用 + API 服务 + 后台 Worker 的形态。

**后果**：应用代码放在 `app/`，前端负责工作台，后端负责任务和媒体流水线，FFmpeg 在服务端执行媒体处理。

**验证**：用户可以通过 Web 创建任务、查看进度、预览和下载成片。

---

### D003：使用编导 Agent、Reviewer Agent 与 Skill Pipeline，而不是复杂多 Agent 编排

**日期**：2026-05-05  
**状态**：已采纳  
**决策者**：项目创建者

**背景**：自动化视频生产需要创作判断和质量审核，但第一版不应引入复杂 Agent 网络。

**选项**：
1. 多 Agent 编排平台。优点是角色完整；缺点是复杂度高、调试困难、过早抽象。
2. 单一线性 Pipeline。优点是简单；缺点是创作和审核判断边界不够清晰。
3. 编导 Agent + Reviewer Agent + Skill Pipeline。优点是保留关键判断角色，同时让执行能力可复用；缺点是需要定义 Skill contract。

**决策**：采用编导 Agent、Reviewer Agent 与 Skill Pipeline。

**后果**：编导和 Reviewer 负责判断，配音、素材提取、素材匹配、字幕、封面和合成作为 Skills。新增视频类型优先组合 Skills。

**验证**：每个 Skill 能独立测试；编导和 Reviewer 的输出能被任务流程消费并在 Web 端展示。

---

### D004：第一版直接使用用户提供链接素材，版权判断由用户负责

**日期**：2026-05-05  
**状态**：已采纳  
**决策者**：项目创建者

**背景**：知识分享视频需要素材与旁白匹配。第一版用户倾向提供相关视频链接，并希望系统直接截取和合成。

**选项**：
1. 直接使用用户提供链接素材。优点是自动化强；缺点是版权和平台下载限制风险高。
2. 推荐片段后人工确认。优点是风险较低；缺点是自动化体验下降。
3. 只参考链接不直接使用。优点是合规风险低；缺点是难以生成完整成片。

**决策**：第一版直接使用用户提供链接素材，但明确用户负责素材使用权，系统不承诺自动版权判断。

**后果**：产品和验证必须包含素材权利边界提示；若链接不可下载，系统应给出明确失败原因。

**验证**：使用用户提供的可下载素材链接完成素材提取、匹配和合成；界面和文档清楚提示素材使用权责任。

## Eureka Moments（突破性发现）

当前没有 Eureka Moment。


---

### D005：吸收参考项目实践：任务产物、步骤状态、审核界面和 Skill contract 优先

**日期**：2026-05-05  
**状态**：已采纳  
**决策者**：项目创建者

**背景**：在进入第一个 feature 前，复核了 `resources/` 下的 MoneyPrinterTurbo、AutoClip、FireRed-OpenStoryline、ai-video-editor、videocut-skills、Remotion 和 OpenCut。

**选项**：
1. 照搬 OpenStoryline 式复杂节点/Agent 编排。优点是能力完整；缺点是第一版过重。
2. 照搬 MoneyPrinterTurbo 式脚本到视频流水线。优点是简单；缺点是审核、素材匹配和可追踪性不足。
3. 保留本项目线性 Skill Pipeline，同时吸收参考项目的任务产物、步骤状态、审核界面、字幕时间戳和 Skill contract。优点是复杂度可控，并解决媒体系统真实工程问题；缺点是需要从第一版就设计 artifact 管理。

**决策**：采用选项 3。

**后果**：首个功能候选必须包含任务状态和 artifact 管理边界；后续 Skill 输出不能只返回内存对象，必须写入可追踪产物。Reviewer Agent 输出必须定位到文案、分镜、字幕、素材片段或视频时间段。

**验证**：第一个 feature 的 design 和 tasks 必须覆盖任务 artifact 目录、步骤状态、失败重试、至少一个可审阅中间产物和边界级验证。

---

### D006：Per-segment TTS with edge-tts word boundary timing

**日期**：2026-05-05
**状态**：已采纳
**决策者**：Architect

**背景**：Feature 004 需要从分镜旁白文本生成配音音频，同时需要精确的 word-level 时间戳用于字幕生成和素材匹配。

**选项**：
1. 整段文本生成 TTS + Whisper ASR 转录。优点是实现简单；缺点是引入额外依赖、转录精度不确定。
2. 逐 segment 生成 TTS 并捕获 word boundary。优点是精确时长和词级时间戳；缺点是需要多次 TTS 调用和音频拼接。

**决策**：逐 segment 生成 TTS，利用 edge-tts Communicate.stream() 的 WordBoundary 事件捕获时间戳。

**后果**：edge-tts 为 async API，需 asyncio.run() 包装；引入 edge-tts 依赖。

**验证**：voiceover skill 单元测试验证音频生成和 timing data 结构。

---

### D007：edge-tts timing for subtitles (no Whisper)

**日期**：2026-05-05
**状态**：已采纳
**决策者**：Architect

**背景**：字幕生成需要时间戳。Feature 原始需求列出 faster-whisper 作为候选依赖。

**选项**：
1. 使用 faster-whisper ASR 转录配音音频。优点是独立于 TTS 引擎；缺点是引入大模型依赖、转录可能不准确。
2. 使用 edge-tts word boundary timing 直接生成 SRT。优点是精确、无额外依赖；缺点是与 TTS 引擎耦合。

**决策**：使用 edge-tts timing 直接生成 SRT，不引入 faster-whisper。

**后果**：字幕精度取决于 TTS timing 质量；减少一个重依赖。

**验证**：subtitle skill 单元测试验证 SRT 格式和时间戳正确性。

---

### D008：Fixed-duration clip extraction + sequential duration-based matching

**日期**：2026-05-05
**状态**：已采纳
**决策者**：Architect

**背景**：需要将源视频切分为片段并匹配到配音 segment。

**选项**：
1. 基于场景检测的智能切片。优点是内容感知；缺点是过度设计、依赖额外库。
2. 固定时长切片 + 顺序时长匹配。优点是简单可预测；缺点是匹配精度一般。

**决策**：固定 ~5s 切片，按 voiceover segment 时长顺序分配 clips。

**后果**：知识分享类视频对画面匹配精度要求不高，可接受。

**验证**：material_match 单元测试验证匹配算法正确性。

---

### D009：FFmpeg concat demuxer for video composition

**日期**：2026-05-05
**状态**：已采纳
**决策者**：Architect

**背景**：需要将匹配的素材片段、配音音频和字幕合成为最终视频。

**决策**：使用 FFmpeg concat demuxer + inpoint/outpoint 拼接片段，单命令叠加音频和烧录字幕。

**后果**：FFmpeg 是唯一的合成依赖；长视频合成耗时 30-60s。

**验证**：video_compose 单元测试（mock FFmpeg）+ E2E 测试（real FFmpeg）。

---

### D010：No source videos → solid color fallback

**日期**：2026-05-05
**状态**：已采纳
**决策者**：Architect

**背景**：当无源视频（下载失败且无上传）时，管线需要仍能产出可播放视频。

**决策**：使用 FFmpeg lavfi color source 生成纯色背景视频，叠加配音和字幕。

**后果**：视觉效果差但满足 MVP 可预览可评估目标。

**验证**：E2E 测试覆盖无素材场景，验证 final_video artifact 存在且可播放。
