---
name: bewater-init
description: 初始化 BeWater 项目结构，通过对话引导生成 vision.md、architecture.md 和 constitution.md，Use when 需要初始化 BeWater 项目结构或项目尚未初始化时
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
user-invocable: true
context: project root + templates/00-project + workflow ssot
effort: medium
---


# BeWater Init

初始化 BeWater 项目结构，并通过对话构建项目北极星文档。

## Responsibilities
- initialize `.bewater/` project structure
- create baseline artifacts
- run foundation review
- Generate initial `docs/00-project/product-plan.md` as the durable feature-candidate planning layer
- recommend the first MVP slice from the reviewed project foundation and record it in product-plan
- advance to `initialized` only when `foundation_gate = passed` and product-plan semantic check passes

## Vision Discovery Protocol

`/bewater-init` must not ask the user to fill `vision.md` as a form. It must use adaptive discovery:

1. Determine project mode first:
   - commercial product
   - internal tool
   - side project / demo
   - open source / community
   - learning / exploration
   - custom
2. Ask for open intent in the user's own words.
3. Reflect back the inferred intent before narrowing:
   - "我理解你不是想做 [X]，更像是想解决 [Y]，核心矛盾是 [Z]。这个理解对吗？"
4. Fill fixed vision slots with adaptive questions:
   - Project Mode
   - Core Intent
   - Target User
   - Core Problem
   - Current Alternative
   - Core Promise
   - Narrowest Wedge
   - Product Principles
   - Direction: Now / Next / Later
   - Non-goals
   - Success Signals
   - Open Assumptions
5. Ask one blocking question at a time.
6. Prefer multiple choice when the user is unsure.
7. Challenge vague answers such as "所有人", "创作者", "提高效率", or "做一个平台".
8. Capture unresolved but accepted uncertainty in `Open Assumptions` instead of continuing indefinitely.
9. Do not create `prd.md`, do not call the result PRD, and do not create date-based roadmap commitments.

## Re-entry
- rerunning `/bewater-init` is the canonical repair path after `foundation_gate = failed`
- baseline artifact creation must be idempotent over existing files

## When to Activate

- 新项目开始
- 需要初始化 BeWater 结构
- 项目尚未初始化（无 `.bewater/` 目录）

## When NOT to Activate

- 项目已经初始化（存在 `.bewater/` 目录，且 `docs/00-project/` 下文档已填写）
- 正在执行其他 BeWater 命令

## 职责边界（强制约束）

### ✅ 必须做

1. 创建 `.bewater/` 目录和配置文件
2. 创建 `docs/` 目录结构
3. 将 `00-project` 模板复制到 `docs/00-project/`
4. **阶段一**：对话式引导用户填写 `vision.md`（产品愿景）
5. **阶段二**：对话式引导用户填写 `architecture.md`（项目级全局技术约束）
6. **阶段三**：对话式引导用户确认 `constitution.md`（项目宪法 — 不可变原则）。模板已预填 5 条 BeWater 默认原则（Evidence-First Delivery、User-Visible Slice First、Simplicity Over Speculation、Use Existing Architecture Directly、Boundary Validation），用户可确认采纳、删除不适用的、或新增项目特有的原则。原则数量建议 3-7 条
7. 清理并初始化 `decision-log.md`，不得保留示例占位符、跨项目经验或与当前项目无关的条目
8. 生成并持久化 `docs/00-project/foundation-review.md`
9. 生成并持久化 `docs/00-project/product-plan.md`，作为 `vision.md -> feature.md` 之间的项目级规划层
10. 从 `vision.md` 的 MVP、Project Mode、Target User、Core Problem、Core Promise、Narrowest Wedge、Direction / Now、Product Principles、Success Signals、Non-goals 和 Open Assumptions 中生成 2-3 个 MVP-first feature candidates，写入 `product-plan.md`
11. 在 `product-plan.md` 中明确 `MVP Learning Loop`、`Feature Candidate Map`、`Recommended Next Feature`、`Dependency / Sequencing Notes` 和 `Plan Change Log`
12. 写入 `foundation_gate`，检查 north star clarity、architecture constraints coherence、constitution completeness、decision-log template cleanup、product-plan completeness、placeholder removal、application_root path alignment 与项目层文档矛盾
13. 验证项目层文件已填写完整，`foundation_gate.status = passed`，`python3 .claude/scripts/bewater-check.py product-plan --project-root .` 通过，且 `product-plan.md` 至少有一个 recommended candidate
14. 告知用户"初始化完成，请先确认 product-plan.md 中的 Recommended Next Feature；确认后运行 /bewater-goal PC-001 创建第一个功能目标"

**重要说明**：
- `architecture.md` 是**项目级全局文档**，定义整个项目的技术栈、架构约束、非功能需求
- `architecture.md` 中所有应用代码路径必须和 `.bewater/install-meta.json` 的 `application_root` 一致；如果 `application_root=app`，目录树必须写 `app/src/...`，或明确注明路径相对于 `application_root`（`app/`）
- Web / frontend 项目的 Core Web Vitals 必须使用 LCP、CLS、INP；不能使用已废弃的首次输入延迟指标
- 安全约束不能声明无 XSS 风险；静态站点也必须说明无运行时用户提交表单、Markdown HTML 策略、CSP、外链/iframe/第三方脚本策略
- `constitution.md` 定义**不可变项目原则**，所有功能和架构决策必须遵守
- 所有后续功能开发都必须遵循此文档的技术约束
- 首个功能候选只是初始化后的交接建议，不是 feature spec；用户确认前不得进入 `/bewater-goal`

### ❌ 禁止做

1. 不能覆盖现有已填写文件
2. 不能写代码 — 只初始化结构和文档
3. 不能生成 feature.md — 这是 /bewater-goal 的职责
4. 不能跳过对话 — 必须与用户对话
5. 不能要求用户凭空提出第一个功能；必须基于 foundation review 给出候选切片

## 状态转换

- **前置状态**: 无（全新项目）
- **后置状态**: `initialized`（目录 + 项目层文档已就绪）
- **下一步命令**: 先确认首个功能候选，再运行 `/bewater-goal`

## 输出合约

```json
{
  "status": "passed|failed|blocked",
  "artifacts": {
    "vision_path": "docs/00-project/vision.md",
    "product_plan_path": "docs/00-project/product-plan.md",
    "architecture_path": "docs/00-project/architecture.md",
    "constitution_path": "docs/00-project/constitution.md",
    "decision_log_path": "docs/00-project/decision-log.md",
    "foundation_review_path": "docs/00-project/foundation-review.md"
  },
  "gate": {"name": "foundation_gate", "status": "passed|failed|blocked"},
  "product_plan": {
    "recommended_next_candidate": "PC-001",
    "mvp_learning_loop_defined": true,
    "human_confirmation_required": true,
    "next_action": "confirm product-plan recommended candidate -> /bewater-goal PC-001"
  },
  "blockers": [],
  "next_action": "confirm product-plan recommended candidate -> /bewater-goal PC-001"
}
```


**版本**: 4.0.0 | **最后更新**: 2026-04-30
