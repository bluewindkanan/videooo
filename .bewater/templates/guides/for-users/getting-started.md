# 快速开始

> 面向第一次使用 BeWater 的用户。

## 目标

在 10 分钟内跑通一条标准流程：`init -> goal -> plan -> build -> validate -> ship -> learn`。

Public path: `init -> goal -> plan -> build -> validate -> ship`
Public validation path: `goal -> plan -> build -> validate -> ship`

vNext command sequence:
1. `/bewater-init`
2. 确认 `foundation-review.md` 中的首个功能候选
3. `/bewater-goal 001`
4. `/bewater-plan 001`
5. `/bewater-build 001`
6. `/bewater-validate 001`
7. `/bewater-ship 001`
8. `/bewater-learn 001`

Optional helpers:
- `/bewater-next`
- `/bewater-auto`

默认 `/bewater-auto` 只有两个必须停下来的人工闸口：goal 需求确认，以及 ship 前的 release decision。其余 `plan -> build -> validate -> ship precheck` 在无阻断时自动推进。

## 前置条件

- 已有项目代码仓库
- 项目根目录已安装 BeWater 模板与 Skills
- 需要从安装后的项目根启动 Claude Code，确保 `.claude/skills/` 被识别为当前项目的 project-level skills

## 步骤

0. 进入安装后的项目根并启动 Claude Code
   - `cd /path/to/your/project`
   - `claude`

1. 初始化项目基础
   - 运行 `/bewater-init`
   - 产出 `docs/00-project/foundation-review.md`
   - 确认或调整其中推荐的首个功能候选

2. 定义功能目标
   - 运行 `/bewater-goal`
   - 产出 `docs/01-features/001-xxx/feature.md`

3. 生成任务拆解
   - 运行 `/bewater-plan 001`
   - 产出 `docs/01-features/001-xxx/tasks.md`

4. 开始开发实现
   - 运行 `/bewater-build 001`
   - 持续更新 `tasks.md` 进度

5. 验证实现
   - 运行 `/bewater-validate 001`
   - 产出 `docs/01-features/001-xxx/validation-report.md`
   - 写入 `runtime.validation_outcome`，不执行发布

6. 核验证据并发布
   - 运行 `/bewater-ship 001`
   - 消费 validate 证据；证据缺失或过期时会自动补齐或刷新
   - 只有证据齐全且 gate 通过时才会进入 `shipped`

对 user-visible features，验证不止检查“功能存在”。还必须检查用户能发现入口，并能走通最小使用路径。

### What `/bewater-ship` Does

`/bewater-ship` ships the current validated feature/slice to the release boundary declared in `.bewater/release.json`.

- Default `local`: writes release record and local commit; no push or deploy.
- `git_push`: pushes to the configured Git remote after irreversible acknowledgement.
- `script`: runs the configured deploy/publish script after irreversible acknowledgement.

Run `/bewater-ship --precheck-only` to preview the release plan without commit, push, deploy, publish, or script execution.

7. 学习回写
   - 运行 `/bewater-learn 001`
   - 更新 `docs/02-learning/` 下文档

## 已有实现如何接入

已有实现（existing implementation）不需要额外命令：

1. 运行 `/bewater-goal`，写明 `implementation_mode`
2. 运行 `/bewater-plan`，判断是补缺口还是直接验证
3. 只有发现缺口时才进入 `/bewater-build`
4. 其余情况下继续 `/bewater-validate`，再进入 `/bewater-ship`

## 常见卡点

- 看不到 `001-xxx`：先运行 `/bewater-goal`
- 无法进入发布：运行 `/bewater-ship` 并查看 `validation-report.md` 的阻断项
- 学习阶段报错：确认状态已是 `shipped`
