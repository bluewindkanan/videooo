# Release Record: 002-AI 编导管线

feature_id: 002
feature_name: AI 编导管线（LLM 文案/分镜/审查 + 可用 Web 工作台）
released_at: 2026-05-05
release_boundary: local
release_decision: go

## What Was Delivered

- LLM Skill Adapter（OpenAI-compatible，支持通义千问/智谱 GLM 切换）
- Script Generation Skill（LLM 生成短视频文案：hook/body/CTA/时长）
- Storyboard Skill（基于文案生成分镜表：旁白/画面/关键词/时段）
- Review Script Skill（LLM 审查文案和分镜，输出结构化 findings）
- StepRunner 重构为 Skill dispatch（3 步管线：script_generation → storyboard → review_script）
- Web 工作台 SPA 升级（任务列表 + 任务详情 + 可读产物展示 + 重试）
- API 扩展（GET /api/video-tasks + GET artifact content）
- AI Eval 基础设施（golden.jsonl + eval runner）

## Evidence Summary

- Tests: 50 passed (43 unit + 7 integration)
- Coverage: 92% line coverage
- TDD receipts: 7/7 valid
- Blackbox smoke: passed
- Review gate: passed (2 blockers fixed)
- AI eval: infrastructure ready (requires LLM_API_KEY for execution)

## Artifacts

| Artifact | Path |
|----------|------|
| feature.md | docs/01-features/002-ai-director-pipeline/feature.md |
| design.md | docs/01-features/002-ai-director-pipeline/design.md |
| tasks.md | docs/01-features/002-ai-director-pipeline/tasks.md |
| prebuild-review.md | docs/01-features/002-ai-director-pipeline/prebuild-review.md |
| review-note.md | docs/01-features/002-ai-director-pipeline/review-note.md |
| validation-report.md | docs/01-features/002-ai-director-pipeline/validation-report.md |
| receipts.json | docs/01-features/002-ai-director-pipeline/receipts.json |
| release-record.md | docs/01-features/002-ai-director-pipeline/release-record.md |

## Files Changed

- app/src/skills/__init__.py (NEW)
- app/src/skills/llm_adapter.py (NEW)
- app/src/skills/script_generation.py (NEW)
- app/src/skills/storyboard.py (NEW)
- app/src/skills/review_script.py (NEW)
- app/src/workers/step_runner.py (MODIFIED)
- app/src/server/routes/video_tasks.py (MODIFIED)
- app/src/server/schemas.py (MODIFIED)
- app/src/storage/sqlite.py (MODIFIED)
- app/src/web/workbench.html (MODIFIED)
- app/src/web/workbench.js (MODIFIED)
- app/tests/unit/test_llm_adapter.py (NEW)
- app/tests/unit/test_script_generation.py (NEW)
- app/tests/unit/test_storyboard.py (NEW)
- app/tests/unit/test_review_script.py (NEW)
- app/tests/unit/test_task_list.py (NEW)
- app/tests/integration/test_api_video_tasks.py (MODIFIED)
- app/tests/blackbox/video_task_smoke.sh (MODIFIED)
- app/evals/002/golden.jsonl (NEW)
- app/evals/run_002.py (NEW)
