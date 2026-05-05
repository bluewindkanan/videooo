# 开发工作流

## 目标

确保 `templates/`、`.claude/skills/`、`.claude/agents/`、`WORKFLOW.md`、`install.sh` 五处始终一致。

## 推荐顺序

1. 先改流程权威定义：`WORKFLOW.md`
2. 再改共享契约：`.claude/skills/SHARED_STATE_CONTRACT.md`
3. 再改执行规则：`.claude/skills/*/SKILL.md`
4. 再改模板：`templates/**`
5. 最后改安装链：`install.sh`

## 必做同步项

- 公开状态链同步：`uninitialized → initialized → specified → planned → building → shipped`
- 命令边界同步：`build -> validate -> ship`（`/bewater-validate` 公开，validate-flow 保持执行归属）
- 公共入口同步：`goal -> plan -> build -> validate -> ship`（ship 在证据缺失或过期时保留 validate-flow 安全兜底）
- artifact 字段同步：`review_note_path`、`validation_report_path`
- 分类字段同步：`complexity_tier`、`implementation_mode`
- 运行时路径同步：统一使用 `.claude/agents/` 与 `.claude/skills/`

## 回归检查

- 旧路径关键字扫描
- 旧术语扫描（如旧预发布阶段名、旧 review artifact 字段）
- Markdown 本地链接有效性扫描
- 安装后 doctor 检查

## Release Adapter Development Notes

Remote effect adapters are opt-in. `git_push` and `script` must be configured in `.bewater/release.json`, previewed, and acknowledged before execution. CI wrappers may provide trusted release intent through `runtime.release_intent`.

## 已有实现模式

已有实现（existing implementation）不新增公开命令，开发侧需要确保：

- Planner 输出 gap analysis，而不是默认把已有代码重做一遍
- Builder 在 existing implementation 模式下只修补缺口
- `/bewater-validate` 可在特定条件下从 `planned` 直接接管，但必须先把状态推进到 `building`

## 风险提示

只改其中一层最容易造成“文档能看但流程跑不通”。
