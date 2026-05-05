# Rubric (001) — lite

目标：对首切片的“编导/Reviewer 输出”做 **可审计** 的最小评估（lite），避免主观点评。

## Schema checks（必须全通过）

对 `script_generation` 的 `script_draft`（JSON）要求：
- 必须包含字段：`hook`, `body`, `call_to_action`, `estimated_duration_seconds`
- `hook/body/call_to_action` 必须为非空字符串
- `estimated_duration_seconds` 必须为正整数

## Minimal quality checks（lite）

- `body` 字符数 ≥ 6（避免空洞）
- `estimated_duration_seconds` 在 [10, 120] 秒之间

通过阈值（align design.md）：
- schema_pass_rate = 1.0
- usefulness_rate ≥ 0.8

