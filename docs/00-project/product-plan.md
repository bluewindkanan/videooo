# Product Plan（产品规划）

> 创建日期：2026-05-05  
> 最后更新：2026-05-05  
> 用途：把 `docs/00-project/vision.md` 的方向拆成可交付的 **用户价值切片**（feature slices），并明确“先做什么/为什么现在做/依赖与风险”。  
> 注意：这是规划（what/why），不是排期；执行细节只出现在各 feature 的 `tasks.md`。

## Planning Intent

- **产品北极星**：内容团队从“主题/文案/文章链接 + 用户提供素材（链接/上传）”出发，获得“可预览、可下载、接近可发布”的知识分享类短视频初稿。
- **规划约束**（见 `constitution.md`）：Workflow over editor、Reviewable automation、Artifact-first、Rights-aware inputs。
- **规划输出**：用“候选切片表 + 推荐下一切片 + 依赖说明”来驱动 `/bewater-goal` 的选择与收敛。

## MVP Learning Loop

我们用“可观测 → 可审查 → 可控质量 → 可证明效率”的学习闭环推进：

1. **闭环可用**：创建任务 → 看到进度 → 有关键中间产物 → 能导出成片（允许质量一般，但必须可复盘）。
2. **可审查可重试**：失败/质量问题能定位到步骤与片段；支持局部重跑；保留错误留痕。
3. **质量可控**：Reviewer findings 结构化；阻断级问题可明确标记或阻断输出。
4. **效率可证明**：用真实样本记录支撑“制作时间下降 ≥ 70%”的结论（不在此文档承诺日期/排期）。

## Feature Candidate Map

> 说明：ID 采用 `PC-xxx`（Product Candidate）。每行必须描述“用户可观察效果”，避免写任务级执行细节。

| ID | Title | User Value | Vision Link | MVP Role | Observable Effect | Feedback Value | Priority | Status | Why Now | Risk |
|---|---|---|---|---|---|---|---|---|---|---|
| PC-001 | Knowledge Task Skeleton | 把“任务/步骤/产物/下载”变成可见、可验证的最小闭环骨架 | `docs/00-project/vision.md#Narrowest-Wedge（最小切口）` | 闭环骨架 | 用户能在 Web 创建任务、看到步骤状态，并下载一个导出视频/产物 | 提供端到端链路可观测性，为后续接入真实能力提供落点 | P1 | shipped | 已完成且作为后续所有切片的底座 | 骨架易“看似可用但无真实价值”，需后续切片补齐真实产物 |
| PC-002 | AI Director Pipeline | 让编导/审阅输出可被流水线消费，开始产生”可审查的中间产物” | `docs/00-project/vision.md#Direction（方向，不是排期）` | 核心能力落地 | 任务能生成脚本/分镜/审阅产物（结构化 JSON + findings） | 直接暴露 LLM 质量、素材匹配与审阅机制的真实问题 | P1 | partial_shipped | LLM 步骤已交付。媒体处理管线延后至 PC-007。 | LLM 成本/延迟与输出不稳定；素材链接可用性不确定 |
| PC-003 | 素材两路径与失败分流 | 链接不可解析/不可下载时仍可完成生产（上传替代） | `docs/00-project/vision.md#Open-Assumptions（开放假设）` | 稳定性增强 | 用户在素材失败时得到明确原因，并可切换到上传素材继续推进 | 把”素材不可用”从偶发 bug 变成可管理分支 | P1 | shipped | 素材可用性是首要外部不确定性，必须工程化降级 | 上传与存储会引入容量/清理/权限与安全风险 |
| PC-004 | Reviewer 阻断质量门槛 | 把 findings 变成明确的 go/no-go 规则，减少“坏视频被导出” | `docs/00-project/vision.md#Success-Signals（成功信号）` | 质量门槛 | 用户在导出前看到阻断问题（脚本/字幕/事实/匹配），并可选择修复或承认风险 | 提升反馈质量，避免浪费合成与审核时间 | P2 | candidate | 当闭环可用后，下一步是把质量从“主观”变为“可控” | 过严会阻塞生产；过松则无意义，需要迭代阈值 |
| PC-005 | Artifact 浏览与对比体验 | 降低定位成本，让“审阅/修复/重试”更像工作台而不是日志地狱 | `docs/00-project/vision.md#Reviewable-Automation（可审查的自动化）` | 可用性增强 | Web 可查看脚本/分镜/字幕/日志与关键片段，并能对比重跑前后差异 | 收集“问题类型/频率”作为后续优化输入 | P2 | candidate | 进入日常使用前必须降低调试门槛 | UI/存储/索引复杂度上升；需控制范围 |
| PC-006 | 小规模 Eval 与回归资产 | 让质量迭代可回归，而非只靠”主观观感” | `docs/00-project/vision.md#Direction（方向，不是排期）` | 可持续迭代 | 每次改动后能跑一组固定样本，产出对比报告（RED/GREEN） | 把”质量提升”变成可度量工程工作 | P3 | candidate | 当链路跑通后，尽早建立最小回归机制 | Eval 设计不当会误导优化方向 |
| PC-007 | 媒体管线核心 | 从结构化产物到可预览、可下载的视频初稿，补齐 MVP 核心缺口 | `docs/00-project/vision.md#Narrowest-Wedge（最小切口）` | MVP 闭环 | 用户提交主题后，系统生成带配音、背景画面、字幕的完整视频初稿 | 首次暴露真实音频质量、素材匹配效果和成片质量问题 | P1 | recommended | PC-002 LLM 部分 + PC-003 素材双路径已交付，前置条件满足 | FFmpeg 环境差异；TTS 中文质量；素材片段不足需循环拼接 |
| PC-008 | 封面生成与成片审查 | 完整的视频初稿体验（封面 + 质量审阅） | `docs/00-project/vision.md#Reviewable-Automation（可审查的自动化）` | 质量增强 | 任务产出包含封面图和成片质量审阅结果 | 暴露成片质量问题（字幕错位、画面不匹配、音频问题） | P2 | candidate | 媒体管线跑通后立即需要成片质量反馈 | 封面样式需迭代；review_video 需要 LLM 理解视频内容 |

## Recommended Next Feature

- candidate_id: PC-007
- rationale: PC-002 LLM 部分 + PC-003 素材双路径已交付，PC-007 补完”输入主题 → 输出视频”的 MVP 闭环，兑现 PC-002 原始承诺中的”导出成片初稿”。
- success_definition: 用户提交主题 + 素材链接后，系统产出带配音、背景画面、字幕的完整视频初稿（.mp4），可预览和下载。每个中间步骤写入独立 artifact，失败可重试。

## Dependency / Sequencing Notes

- PC-001 是其他切片的前置：没有步骤状态与产物体系，就无法做可审查与可重试。
- PC-002 LLM 部分已交付；媒体处理部分延后至 PC-007。
- PC-007 依赖 PC-002 LLM 部分（已交付）+ PC-003 素材双路径（已交付），前置条件已满足。
- PC-008 依赖 PC-007（需要最终视频才能做封面和成片审查）。
- PC-002 完成后，才能判断 PC-004（质量门槛）与 PC-006（回归资产）的最小有效形态；否则容易在”空目标”上做评测或 gate。
- PC-003 与 PC-007 强相关：素材获取失败会直接影响视频合成，但上传替代路径已可用。
- PC-005（工作台体验）应在”问题类型稳定出现”后再做，否则 UI 容易先于需求固化。

## Not Yet Ready Candidates

> 这些候选暂不进入近期主线：要么边界未定义清楚，要么风险/依赖尚未具备。

- 口播视频自动剪辑（需要稳定的镜头切分/口播节奏与字幕对齐策略，且验证成本高）
- 产品介绍视频（需要产品素材与事实校验策略，且更易触及合规/宣称风险）
- 自动搜集网络素材（会显著扩大版权与稳定性风险，违背当前最小切口）

## Completed / Superseded Candidates

- PC-001（shipped）：已交付任务骨架切片，作为后续切片的基础设施与审计底座。
- PC-002（partial_shipped）：LLM 编导/分镜/审查已交付；媒体处理管线延后至 PC-007。
- PC-003（shipped）：已交付素材两路径与失败分流。
