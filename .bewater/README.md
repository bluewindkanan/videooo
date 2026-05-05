# BeWater Methodology

> **Agent + Validation Driven Product Development Methodology**
> 面向 1-5 人小团队的 Agent 驱动、验证闭环优先的产品开发方法论（6-15 人可作为扩展场景）

Version: 4.0.0
Published: 2026-04-30

Public path: `init -> goal -> plan -> build -> validate -> ship`
Public validation path: `goal -> plan -> build -> validate -> ship`

BeWater 4.0.0 strengthens the existing pre-build boundary with convergence checks. `/bewater-plan` still owns `prebuild_review_gate`, but that gate now includes spec convergence, required human intent confirmation, user-value split checks, rework-risk routing, and a global coverage matrix in `prebuild-review.md`.

BeWater exposes 6 public lifecycle commands: init, goal, plan, build, validate, and ship. It also exposes 6 public utility commands, 3 internal flow skills, and 6 capability-pack skills.

Public utility commands include `/bewater-auto`, `/bewater-next`, `/bewater-status`, `/bewater-learn`, `/bewater-quick`, `/bewater-eval`.

Default `/bewater-auto` has only two human gates: goal confirmation and the release decision before execution. The `plan -> build -> validate -> ship precheck` path proceeds automatically unless blocked.

Ship modes:
- `/bewater-ship 001`
- `/bewater-ship 001 --precheck-only`（审计/CI，仅检查不发布）

### Release Boundary

BeWater ships to the configured release boundary in `.bewater/release.json`.
Default is local release record plus commit. Enabling `git_push` means `/bewater-ship` pushes to the configured Git remote after acknowledgement. Enabling `script` means `/bewater-ship` runs the configured deploy or publish script after acknowledgement.

For user-visible features, BeWater validation does not stop at technical existence. It must also verify that the capability can be discovered and that a normal user can complete the minimal intended usage path.

### AI Behavior Eval Track

For features that ship LLM, model, RAG, recommender, classifier, or AI agent behavior, BeWater adds a conditional AI Behavior Eval Track inside the same public path: `goal -> plan -> build -> validate -> ship`.

This track is eval-first for AI behavior:

- Goal records `ai_behavior_eval` applicability and risk.
- Architect writes `AI Behavior Evaluation Strategy`.
- Plan writes `Eval Asset Map`.
- Build creates eval assets and records Eval RED/GREEN evidence.
- Validate runs and audits planned eval assets in `AI Behavior Evaluation Results`.

This introduces **no new public command**, public state, or release gate. Ordinary deterministic features keep the existing TDD + Validate workflow.

### What `/bewater-ship` Does

`/bewater-ship` ships the current validated feature/slice to the release boundary declared in `.bewater/release.json`.

- Default `local`: writes release record and local commit; no push or deploy.
- `git_push`: pushes to the configured Git remote after irreversible acknowledgement.
- `script`: runs the configured deploy/publish script after irreversible acknowledgement.

Run `/bewater-ship --precheck-only` to preview the release plan without commit, push, deploy, publish, or script execution.

Current runtime inventory:

- 20 skills total
- 14 BeWater lifecycle/utility/internal skills
- 6 capability-pack skills: `product-framing`, `planning-readiness`, `review-pack`, `tdd-implement`, `validation-pack`, `evidence-aggregate`
- 8 agents: `SHARED_AGENT_BASE.md`, `architect.md`, `builder.md`, `inspector.md`, `planner.md`, `product.md`, `qa.md`, `reviewer.md`

## Current References

- `docs/reference/command-surface.md`
- `docs/reference/runtime-contracts.md`
- `docs/reference/skill-agent-inventory.md`
- `docs/reference/capability-packs.md`
- `docs/reference/semantic-gates.md`
- `docs/reference/release-intent-policy.md`
- `.bewater/contracts/template-tier.schema.json`
- `docs/maintainers/source-vs-installed-mode.md`
- `docs/maintainers/historical-docs-policy.md`
- `docs/maintainers/methodology-backlog-workflow.md`

版本: 4.0.0 | 日期: 2026-04-30

---

## 一句话描述

BeWater 是一套为 **1-5 人小团队** 设计的 AI 原生开发方法论。

它的核心不是把文档放在中心，而是把 **Agent 执行** 和 **多层验证闭环** 放在中心，让轻量文档承担目标对齐、边界约束和审计沉淀的职责。

---

## 命名直觉

> Be water.

软件开发越来越像在高不确定性环境中持续流动：

- 需求会变化
- 实现路径会变化
- Agent 的能力会变化
- 模型上下文能力会变化
- 但质量门槛不能漂移

BeWater 的意思不是"没有结构"，而是：

- **目标上稳定**
- **执行上灵活**
- **验证上严格**
- **知识上持续沉淀**

---

## 设计目标

### 目标用户

- 1-5 人软件产品团队（主场景）
- 6-15 人软件产品团队（扩展场景）
- 同时使用人类开发者和 AI Agent
- 需要在速度和质量之间取得平衡
- 需要团队协作、交接、复盘和持续演进

### 适用范围

- 通用软件产品开发
- Web / App / API / 后端系统
- 新产品开发
- 存量系统迭代
- 中等复杂度到高复杂度业务功能

### 解决的问题

1. 纯 Spec 驱动文档重，执行慢
2. 纯 Agent 驱动效率高，但容易失控
3. 只靠测试无法覆盖真实产品质量
4. 团队协作时，知识和结论容易停留在会话里，无法沉淀

---

## 核心判断

### 判断 1：Spec 仍然需要，但不再是中心

文档不会消失，因为团队协作仍然需要显式边界、成功定义和审计链。

但 Spec 不应该继续承担主执行逻辑。它更适合作为：

- 目标对齐层
- 约束层
- 验收基线
- 知识沉淀层

### 判断 2：Agent 会成为主要执行系统

随着模型和代理能力增强，开发主循环会从：

`人写计划 -> 人写代码 -> 人测试`

转向：

`人定义目标 -> Agent 规划与执行 -> 人做关键裁决`

### 判断 3：真正的卡点在验证

未来软件开发最难的不是"生成代码"，而是判断：

- 这个产品到底行不行
- 这个设计是否真正解决问题
- 这个实现是否能稳定上线
- 这个变更是否引入安全和性能风险

所以 BeWater 的主心骨不是 Spec，也不是 Agent，而是：

**Agent 驱动执行 + Validation 驱动完成**

---

## 核心框架

BeWater 采用三层核心结构，加一个持续学习回路，并映射为 9 阶段工作流（含项目初始化和架构设计）。

```text
Goal / Constraints
    |
Agent Planning & Execution
    |
Multi-Layer Validation
    |
Write-back & Learning
```

### Layer 1: Intent Layer

作用：定义目标、边界、成功标准。

建议工件：

- `feature.md`
  - 用户问题
  - 业务目标
  - 范围边界
  - 非目标
  - 验收场景
  - 成功标准
  - 风险提醒
- `architecture.md`（按需）
  - 只在复杂功能或高风险系统启用

设计原则：

- 轻量必需
- 只写会影响执行和验收的内容
- 避免为写文档而写文档

### Layer 2: Agent Execution Layer

作用：让多角色 Agent 成为主要执行系统。

实际 Agent 角色（`.claude/agents/`）：

- `product.md` — Product Agent
  - 重构需求、挑战范围、发现错误 framing
- `architect.md` — Architect Agent（按需）
  - 技术架构设计、技术选型、模块划分
- `planner.md` — Planner Agent
  - 任务拆解、依赖分析、readiness review 与 pre-build convergence
- `builder.md` — Builder Agent
  - 实现代码、补齐测试、推进交付
- `reviewer.md` — Reviewer Agent
  - 代码审查、设计偏差审查、回归风险检查
- `qa.md` — QA Agent
  - 场景验证、接口验证、浏览器验证
- `inspector.md` — Inspector Agent
  - 质量巡检、一致性检查、状态验证
- `SHARED_AGENT_BASE.md` — 共享基础定义
  - 所有 Agent 共用的职责边界、输出格式、禁止项

设计原则：

- Agent 不是自由放养
- Agent 必须在 Intent Layer 的边界内工作
- 超出范围的建议，必须升级为人工决策

### Layer 3: Validation Layer

作用：成为整个方法论的最终裁判层。

默认验证栈：

- `Smoke Test`
  - 应用启动检查
  - 健康检查端点
  - 关键路由可访问性
- `Tests`
  - 单元测试
  - 集成测试
  - 契约测试
- `Scenario QA`
  - 真实用户路径
  - 页面交互
  - 端到端流程
- `Security`
  - 权限
  - 注入
  - 数据泄露
  - 危险操作
- `Performance`
  - 响应时间
  - 关键路径性能
  - 资源消耗
- `Acceptance`
  - 是否满足目标
  - 是否满足业务预期

设计原则：

- `Done != Code Written`
- `Done != Tests Passed`
- `Done = Validation Passed`

### Learning Loop: Write-back & Learning

作用：让每次开发都形成团队复利。

写回对象：

- 目标和范围变化 -> `feature.md`
- 验收经验 -> `feature.md`
- 架构结论 -> `architecture.md`
- 风险模式 -> `decision-log.md`
- 回归场景 -> 测试和 QA 资产

---

## 标准工作流

本节是面向使用者的 5 步简化视图：Goal -> Plan -> Build -> Validation -> Learning。进入这 5 步前，`/bewater-init` 会先完成 foundation review 并给出首个功能候选，用户确认后再进入 `/bewater-goal`。完整生命周期仍是 9 阶段：Init -> Goal -> Architecture -> Plan -> Build -> Review -> Validate -> Ship -> Learn；Architecture、Review、Validate 多数情况下由核心命令内部触发或吸收。

### 1. Goal Framing

输入：模糊需求、业务想法、问题描述

产出：

- `feature.md`

完成标准：

- 团队清楚"要做什么"
- 团队清楚"什么叫做成了"

### 2. Plan Under Constraints

输入：

- `feature.md`
- `architecture.md`（如已有）

Agent 动作：

- 拆解任务
- 识别依赖
- 标记高风险点
- 必要时补 `architecture.md`
- 完成 `feature.md + design.md + tasks.md` 的 pre-build readiness review

产出：

- `tasks.md`
- `design.md`
- `architecture.md`（按需）

计划契约：

- BeWater 不使用独立 `execution-plan.md`
- `tasks.md` 是唯一 execution-facing 计划工件，由 `Delivery Map` 和 ready task 的 `Execution Block` 组成
- 每个任务必须显式写 `task_readiness: backlog | ready | in_progress | done`
- `tasks_gate=passed` 仅表示下一组 dispatchable ready tasks 已可执行（build 无需再补齐执行细节）
- `/bewater-plan` 只有在 pre-build readiness review 无 blocker 时，才能把 `tasks_gate` 写为 `passed`

### 3. Agentic Build

Agent 动作：

- 按任务并行或串行实现
- 自动生成或补齐测试
- 持续进行代码审查

约束：

- 影响范围和目标的变化，必须上提到人
- 不能只改代码不改约束文档

### 4. Validation Gate

执行：

- 跑测试
- 跑 QA 场景
- 跑安全检查
- 跑性能检查
- 做最终业务验收

产出：

- `validation-report.md`

要求：

- 必须明确阻断项
- 必须明确剩余风险
- 必须明确是否允许发布
- 门禁标准基于任务风险等级（在 tasks.md 中定义质量策略）

### 5. Write-back & Learning

动作：

- 把关键结论回写
- 把失败样例变成回归用例
- 把高价值经验沉淀为模式

---

## 标准工件

### 必需工件

**项目层**（一次性，`/bewater-init` 生成）：
- `vision.md` - 产品北极星：通过 Vision Discovery 生成，记录 Core Intent、Target User、Core Problem、Core Promise、Narrowest Wedge、Product Principles、Direction、Non-goals、Success Signals 和 Open Assumptions。它不是 PRD，也不是排期 roadmap。
- `architecture.md` - **项目级全局技术约束**（所有功能开发必须遵循）
- `constitution.md` - **项目宪法**（不可变原则，所有功能和架构决策必须遵守）
- `decision-log.md` - 决策记录（Init 阶段生成）

**功能层**（每个功能）：
- `feature.md` - Feature 目标与方案选择：通过 Feature Option Framing 生成，记录 Goal、Vision Link、User Scenario、Proposed Options、Selected Approach、Scope、Non-goals、User Stories、GWT Scenarios 和 AC。它不是 PRD；它是进入设计前的源需求契约。
- `design.md` - **HOW**（技术方案、API 设计、数据模型、架构决策）
- `tasks.md` - **IMPLEMENTATION**（唯一 execution-facing 计划工件，包含 `Delivery Map`、ready task 的 `Execution Block` 与 `Pre-Build Readiness Review`）
- `validation-report.md` - 验证报告（整合测试、代码审查、安全、性能）

**学习层**（项目结束时）：
- `patterns.md` - 成功模式
- `anti-patterns.md` - 失败教训
- `retrospective.md` - 复盘记录

### 状态机

6 个核心状态：

`uninitialized → initialized → specified → planned → building → shipped`

状态推进规则：

- 没有 `vision.md` + `architecture.md` + `constitution.md`，不能进入 `specified`
- 没有 `feature.md` + `design.md`，不能进入 `planned`
- 没有 `tasks.md` 或 `Pre-Build Readiness Review` 未完成，不能进入 `building`
- `building` 内部自动执行 implementing -> review -> validating/prechecking
- `/bewater-ship` 内部补齐/刷新 validate 证据，gate 通过且具备发布意图时发布

### Runtime Semantic Hardening

- `bewater-check.py` 是统一语义检查入口，覆盖 `feature`、`design`、`plan` 与 installed `root` 检查。
- `feature.md` 使用 frontmatter scenarios 保存稳定 story/scenario contract；`design.md` 与 `tasks.md` 必须保留这些 scenario IDs。
- `prebuild_review_gate` 现在检查 spec convergence：intent review、split assessment、scenario-to-design/task/test 覆盖，以及全局 Coverage Matrix。
- `implementation_mode` 支持 `greenfield | extension | existing_partial | existing_complete`；`extension` 表示在已有应用上新增行为，必须说明复用点、修改 callsites 与回归覆盖。
- TDD evidence 使用每个 feature 一个 `receipts.json`，任务引用形如 `receipts.json#T001`。
- Feature docs are historical delivery claims, not automatic current-system truth. Agents should load `docs/00-project/project-context.md` first, then treat `feature.md` as current only when `last_verified_commit` and `implementation_paths` still match code evidence.
- `bewater-check.py feature --project-root <root>` can report `docs_may_be_stale` when declared implementation paths changed after `last_verified_commit`.
- 语义预检路由集中在 `.claude/skills/SHARED_STATE_CONTRACT.md` 的 `Semantic Preflight Matrix`，`/bewater-auto` 必须在失败时停止。
- CI/ship wrappers run the same semantic preflights and return `semantic_preflight_failed` before trusting stored gate state.
- Pending gate 可使用 `produced_by: null`；非 pending gate 必须有非空 producer。`bewater-check.py root` 会校验 `application_root` 是否和真实产品文件位置一致。
- 已 shipped 的旧 feature 默认按迁移安全策略跳过，只有显式 include-shipped 时才纳入语义重检。

---

## 架构

BeWater 采用 **Skills + Agents 两层标准架构**，符合 Claude Code 规范。

### Skills 层（用户入口）

Skills 是用户直接调用的命令，通过 `/skill-name` 触发。每个 Skill 包含 SKILL.md 定义：
- 明确的职责边界
- 详细的执行流程
- 状态转换规则
- 质量检查清单

```
.claude/skills/
├── bewater-init/SKILL.md         # /bewater-init — 项目初始化
├── bewater-goal/SKILL.md         # /bewater-goal — 目标框定
├── bewater-architect/SKILL.md    # /bewater-architect — 架构评估（内部）
├── bewater-plan/SKILL.md         # /bewater-plan — 任务规划
├── bewater-build/SKILL.md        # /bewater-build — Agent 执行
├── bewater-review/SKILL.md       # /bewater-review — 代码审查（内部）
├── bewater-validate/SKILL.md     # /bewater-validate — 多层验证
├── bewater-ship/SKILL.md         # /bewater-ship — 发布
├── bewater-learn/SKILL.md        # /bewater-learn — 学习回写
├── bewater-quick/SKILL.md        # /bewater-quick — 小改动快捷路径
├── bewater-status/SKILL.md       # /bewater-status — 项目状态
├── bewater-eval/SKILL.md         # /bewater-eval — EDD 评估
├── SHARED_EXECUTION_TEMPLATE.md  # 共享执行模板
└── SHARED_STATE_CONTRACT.md      # 共享状态契约
```

### Agents 层（角色定义）

Agents 定义执行者的角色和职责，被 Skills 调用。

```
.claude/agents/
├── product.md          # Product Agent — 目标框定、需求重构
├── architect.md        # Architect Agent — 架构设计、技术选型
├── builder.md          # Builder Agent — 代码实现、TDD
├── reviewer.md         # Reviewer Agent — 代码审查、设计偏差审查
├── qa.md               # QA Agent — 场景验证、质量保证
├── inspector.md        # Inspector Agent — 质量巡检、一致性检查
└── SHARED_AGENT_BASE.md # 共享基础定义（所有 Agent 共用）
```

### 为什么是两层？

1. **Skills 作为入口** - 用户通过 `/bewater-goal` 等命令触发，清晰直观
2. **Agents 作为执行者** - 定义角色职责，可被多个 Skills 调用
3. **职责分离** - Skills 定义"做什么"，Agents 定义"谁来做"
4. **易于维护** - 修改流程只需更新 Skill，修改角色只需更新 Agent

### 正确调用方式

对于 `/bewater-plan` 这类 Skill，仅仅在 `SKILL.md` 中写"调用 Planning Agent"还不够。Skill 必须把"如何委派"写成显式调度指令，否则宿主很容易把它当成描述性文字，直接在主对话里执行规划。

`/bewater-plan` 的正确行为应该是：
- 主 Agent 读取参数和必要文档
- 主 Agent 使用 Agent / Task tool 显式启动子 Agent
- 子 Agent 基于对应的 `.claude/agents/` 定义 + `feature.md` + `design.md` + `architecture.md` 生成 `tasks.md`
- 主 Agent 最后只负责保存结果、更新状态、提示下一步 `/bewater-build`

---

## 安装

```bash
cd 05-implementations/bewater
./install.sh /path/to/your/project
```

这会将 Skills、Agents、Hooks、Scripts、Templates 和流程 SSOT 安装到目标项目。

### 安装内容

| 来源 | 目标位置 | 说明 |
|------|---------|------|
| `templates/` | `.bewater/templates/` | 原始模板（只读参考） |
| `templates/00-project/` | `docs/00-project/` | 项目层文档模板 |
| `WORKFLOW.md` | `WORKFLOW.md` 或 `.bewater/WORKFLOW.bewater.md` | 流程逻辑 SSOT |
| `README.md` | `README.md` 或 `.bewater/README.bewater.md` | 方法论说明（workspace README） |
| `app/README.md` | `app/README.md` | 应用说明（application README） |
| `.bewater/contracts/` | `.bewater/contracts/` | 运行时契约 schema（state/gate/receipt/evidence） |
| `.claude/skills/` | `.claude/skills/` | 20 skills total（14 BeWater lifecycle/utility/internal skills + 6 capability-pack skills） |
| `.claude/agents/` | `.claude/agents/` | 8 agents |
| `.claude/hooks/` | `.claude/hooks/` | 质量门禁钩子 |
| `.claude/scripts/` | `.claude/scripts/` | 辅助脚本 |
| 安装元数据 | `.bewater/install-meta.json` | 记录安装版本、`workflow_doc`、`readme_doc`、`application_root`、`app_readme_doc` 与 doctor 脚本 |

README 安装规则：

- 根 `README.md` 用于方法论/workspace 说明
- 应用说明固定写入 `app/README.md`
- 如果目标项目已有根 `README.md`，安装器会写入 `.bewater/README.bewater.md` 作为方法论文档 fallback

### 启动方式

安装完成后，使用以下任一方式启动 Claude Code：

**方式一：使用启动脚本（推荐）**
```bash
cd /path/to/your/project
./start-claude.sh
```

`start-claude.sh` 由安装器生成，源码目录不直接包含该文件。

**方式二：手动启动**
```bash
cd /path/to/your/project
claude
```

**重要**：只有当前工作目录是安装后的项目根时，`.claude/skills/` 才会被稳定识别为当前项目的 project-level skills。

### 验证技能识别成功

启动后，执行以下命令验证：

```bash
# 应该能识别并触发对应 skill
/bewater-status

# 或者用自然语言
查看当前 BeWater 项目状态
```

如果技能无法识别，请确认：
1. 当前工作目录是项目根目录（含 `.claude/skills/`）
2. Skills 文件存在：`ls .claude/skills/*/SKILL.md`
3. 安装自检通过：`./.claude/scripts/bewater-doctor.sh`

---

## 命令系统

BeWater exposes 6 public lifecycle commands: init, goal, plan, build, validate, and ship. It also exposes 6 public utility commands, 3 internal flow skills, and 6 capability-pack skills.

BeWater 提供 6 个公开生命周期命令：init、goal、plan、build、validate、ship；另有 6 个公开工具命令、3 个内部 flow skills 和 6 个 capability-pack skills。

### 生命周期命令（用户可见）

| 命令 | 阶段 | 作用 | 内部自动调用 |
|------|------|------|-------------|
| `/bewater-init` | 初始化 | 创建项目结构、完成 foundation review、推荐首个功能候选 | - |
| `/bewater-goal` | Goal Framing | 对话式生成 feature.md | -> `/bewater-architect` |
| `/bewater-plan` | Planning | 自动生成 tasks.md | - |
| `/bewater-build` | Build | Agent 执行代码实现（TDD） | -> `/bewater-review` |
| `/bewater-validate` | Validate | 生成验证证据与 `validation_outcome` | -> validate-flow |
| `/bewater-ship` | Ship | 执行 precheck、必要时自动补齐验证证据，并在 release 模式发布 | -> validate-flow fallback |

### 辅助命令

| 命令 | 作用 |
|------|------|
| `/bewater-auto` | Feature 自动化入口：输入需求后推进 goal → plan → build → validate → ship precheck，遇阻断或 release boundary 即停 |
| `/bewater-next` | 只读推荐下一步 |
| `/bewater-status` | 查看项目状态 |
| `/bewater-learn` | 学习回写（可选） |
| `/bewater-eval` | EDD 评估（可选） |
| `/bewater-quick` | 小改动快捷路径（CSS/文案/小重构，跳过 plan，仍要求最小验证） |

### 内部命令（自动调用，对用户隐藏）

| 命令 | 触发时机 | 作用 |
|------|----------|------|
| `/bewater-architect` | `/bewater-goal` 完成后 | 架构评估（智能判断是否需要详细设计） |
| `/bewater-review` | `/bewater-build` 或 `/bewater-quick` 执行中 | 代码内审 |
| `validate-flow` | `/bewater-validate` 或 `/bewater-ship` 安全兜底 | 生成验证证据与 `validation_outcome` |

**注意**：
- 命令名称使用连字符（`-`），不是点号（`.`）
- 内部命令无需用户手动调用，由核心命令自动触发

### 已有实现如何接入

BeWater 不为已有代码新增命令。已有实现（existing implementation）仍然走同一条主链路，只是通过 `implementation_mode` 调整内部路由：

- `greenfield`：`/bewater-goal -> /bewater-plan -> /bewater-build -> /bewater-validate -> /bewater-ship`
- `extension`：复用已有模块，记录 callsites 与回归覆盖，走 `/bewater-build -> /bewater-validate -> /bewater-ship`
- `existing_partial`：先做 gap analysis，再用 `/bewater-build` 补缺口
- `existing_complete`：`/bewater-plan` 可直接把下一步指向 `/bewater-validate`

只有发现真实实现缺口时，才回到 `/bewater-build`，而不是要求把功能重做一遍。

---

## 快速开始

```bash
# 1. 初始化项目
/bewater-init

# 2. 确认 init 输出的首个功能候选后，定义目标（对话式，自动触发架构评估）
/bewater-goal

# 3. 生成任务清单
/bewater-plan

# 4. 执行实现
/bewater-build

# 5. 生成验证证据
/bewater-validate

# 6. 核验证据并发布（证据缺失时仍可内部刷新验证证据）
/bewater-ship

# 或者一键自动化执行
/bewater-auto "添加用户登录功能"

# 默认 /bewater-auto 停在 shippable precheck；只有显式 --with-release 才允许执行 release adapters。

# 小改动快捷路径（跳过 plan，仍要求最小验证）
/bewater-quick 修改按钮颜色
```

> **注意**：架构评估（`/bewater-architect`）是 `/bewater-goal` 的自动步骤，用户无需单独调用。

---

## 团队分工

### 人类负责

- 目标设定
- 范围裁决
- 质量门槛设定
- 风险优先级判断
- 最终放行

### Agent 负责

- 规划
- 实现
- 审查
- 验证执行
- 复盘辅助

### 协作原则

- 人类从"主要编码者"转为"目标设定者 + 决策者"
- Agent 从"辅助工具"转为"执行系统"
- Validation 层成为共同约束

---

## 对标方法论

### 正确的对标对象

BeWater 应该与以下方法论对标：

1. **BMAD (Bug Minimization Architecture Development)**
   - 5 阶段工作流（产品定义、架构设计、开发实现、质量验证、发布）
   - 角色分离（PM、架构师、开发者、QA、DevOps）
   - 文档投入 40-50%
   - 适合 5-20 人团队

2. **Spec-Kit**
   - GitHub 开源的规格驱动工具
   - 支持多种 AI Agent（Claude Code、Cursor、Gemini CLI 等）
   - 提供 constitution、specify、plan、tasks、implement 命令
   - 社区扩展丰富（200+ 扩展）

3. **Ralph Loop**
   - 状态循环驱动的 Agent 自主开发
   - 文档投入 5-10%
   - 适合个人项目
   - 自动化程度最高

4. **Everything Claude Code (ECC)**
   - Agent 生态驱动的开发方法论
   - 多 Agent 协作
   - 适合 3-10 人团队

5. **Claude Agent SDK**
   - Anthropic 官方 SDK
   - 提供 Agent 开发框架
   - 支持多种工具集成

### 不应对标的对象

以下是用户自己的实现，不应作为对标对象：

- **SD Methodology** - 用户自己的规格驱动实现
- **ECC Methodology** - 用户自己的 Agent 生态实现

### 对比优势

| 对比项 | BeWater | BMAD | Spec-Kit | Ralph Loop |
|--------|---------|------|----------|------------|
| 团队规模 | 1-15 人 | 5-20 人 | 1-10 人 | 1-3 人 |
| 文档投入 | 15-20% | 40-50% | 10-15% | 5-10% |
| 自动化度 | 80-90% | 70-80% | 80-90% | 90%+ |
| 学习曲线 | 中等 | 陡峭 | 中等 | 平缓 |
| 质量保障 | 5 层验证栈 | 4 层验证栈 | 3 层验证栈 | 2 层验证栈 |
| 知识沉淀 | 自动提取 | 手动记录 | 项目复盘 | 偶尔复盘 |
| 灵活性 | 渐进式采用 | 固定流程 | 渐进式采用 | 部分定制 |

**BeWater 的核心优势**:
- 平衡效率与质量（比 BMAD 更高效，比 Ralph Loop 更可控）
- 渐进式采用（支持最小配置到完整配置）
- 知识复利机制（自动提取 patterns.md 和 anti-patterns.md）
- 风险分级质量策略（Critical/High/Medium/Low 四级）
- 多层验证闭环（Tests + QA + Security + Perf + Acceptance）

---

## 与传统开发范式的差异

### 传统 Spec-Driven

```text
需求 -> Spec -> Design -> Code -> Test
```

### 纯 Agent-Driven

```text
需求 -> Agent Team -> Code -> Review
```

### BeWater

```text
目标 -> 轻量约束 -> Agent 执行 -> 多层验证 -> 知识回写
```

BeWater 不是取消计划，也不是取消文档，而是把"完成"的定义交给验证层。

---

## 自检与工具

- **版本/阶段一致性**：当前方法论版本 `4.0.0`；标准工作流 9 阶段（Init -> Goal -> Architecture -> Plan -> Build -> Review -> Validate -> Ship -> Learn）。`.claude/skills/bewater-init/SKILL.md` 已对齐。
- **Hooks（可选阻断）**：`hooks/scripts/bewater-hook.js`
  - 检查风险等级与 TDD/覆盖率/Code Review 策略（Critical>=80%, High>=70%, Medium>=60%, Low>=50%）
  - 检查 validation-report 阻断项与发布决策
  - 检查 goal / acceptance / tasks / validation 的追溯链
- **EDD 评估**：`/bewater-eval`
  - 使用 `--baseline` 参数建立基线：`/bewater-eval --baseline`
  - 五维评估：效率/质量/维护/协作/审计

---

## 当前结论

BeWater 的方向已经明确：

- **不是 Spec-Driven**
- **不是纯 Agent-Driven**
- **而是 Agent Execution + Validation Closure**

> **以目标为起点，以 Agent 为执行系统，以验证为最终裁判，以学习回写形成复利。**
