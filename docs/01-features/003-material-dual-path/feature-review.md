---
feature_id: "003"
review_type: feature_definition
reviewed_at: 2026-05-05
reviewed_by: /bewater-goal
status: passed
---

# Feature Review: 003-素材两路径与失败分流

## Review Checklist

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Goal is a user outcome, not a component name | pass | "内容团队提交素材链接后系统自动尝试下载；失败时给出原因并允许上传替代" |
| 2 | Vision Link points to vision.md section | pass | Links to Open Assumptions + Direction / Now |
| 3 | User Scenario names a specific workflow moment | pass | "创建视频任务时提供素材链接，需要自动获取或上传替代" |
| 4 | Proposed Options present trade-offs | pass | A/B/C with recommendation |
| 5 | Selected Approach is confirmed | pass | Option B, confirmed by user |
| 6 | Scope is explicit and verifiable | pass | 8 items in scope, 5 items out of scope |
| 7 | Non-goals are explicit with reasons | pass | Each non-goal has reason |
| 8 | Acceptance Criteria are canonical (AC-xxx) | pass | AC-001 through AC-003, traceable to scenarios |
| 9 | Feature Classification is valid | pass | standard/extension/user_visible |
| 10 | AI Behavior Eval is classified | pass | applicable=false, reason: 确定性文件操作 |
| 11 | Split assessment is calculated | pass | No split conditions triggered, decision=proceed |
| 12 | Intent review is confirmed by user | pass | confirmed by user at 2026-05-05 20:00 CST |
| 13 | Input Constraints are declared | pass | source_links, upload file, failure_category with limits |
| 14 | Risk and dependencies identified | pass | 4 risks with mitigations, 3 external dependencies |

## Concerns

1. 素材下载会引入 HTTP 客户端依赖（aiohttp/httpx），需要在 design.md 明确选型和错误处理策略。
2. 文件上传的安全边界（类型白名单、大小限制、文件名清理）需要在 design.md 中给出具体方案。
3. `waiting_for_material` 状态需要在状态机中定义转换规则（何时进入、何时退出、是否可超时）。
4. material_fetch 排在 script_generation 之前意味着素材获取失败会阻塞 LLM 调用——需要确认这是期望行为（用户已确认）。

## Blockers

无。

## Gate Verdict

**feature_review_gate: passed**

- Feature definition is complete and canonical.
- All required sections present and populated.
- Intent review confirmed by user.
- No blocking issues found.
- Concerns are non-blocking and should be addressed in design.md.
