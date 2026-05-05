#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

echo "[retry-smoke] create task that fails on first attempt"
create_resp="$(curl -sS -X POST "$BASE_URL/api/video-tasks" \
  -H 'content-type: application/json' \
  -d '{"input_kind":"topic","input_text":"FAIL once","source_links":[]}')"
echo "$create_resp"
task_id="$(json_get task_id "$create_resp")"

echo "[retry-smoke] get task detail: $task_id"
detail_resp="$(curl -sS "$BASE_URL/api/video-tasks/$task_id")"
echo "$detail_resp"

status="$(python3 -c "import json,sys; j=json.loads(sys.argv[1]); print(next((s.get('status') for s in j.get('steps', []) if s.get('step_key')=='script_generation'), ''))" "$detail_resp")"
if [ "$status" != "failed" ]; then
  echo "expected script_generation failed before retry; got $status" >&2
  exit 1
fi

echo "[retry-smoke] retry step"
retry_resp="$(curl -sS -X POST "$BASE_URL/api/video-tasks/$task_id/retry" \
  -H 'content-type: application/json' \
  -d '{"step_key":"script_generation"}')"
echo "$retry_resp"
accepted="$(json_get accepted "$retry_resp")"
if [ "$accepted" != "True" ] && [ "$accepted" != "true" ]; then
  echo "expected accepted=true; got $accepted" >&2
  exit 1
fi

echo "[retry-smoke] verify step completed after retry"
detail2="$(curl -sS "$BASE_URL/api/video-tasks/$task_id")"
echo "$detail2"
status2="$(python3 -c "import json,sys; j=json.loads(sys.argv[1]); print(next((s.get('status') for s in j.get('steps', []) if s.get('step_key')=='script_generation'), ''))" "$detail2")"
if [ "$status2" != "completed" ]; then
  echo "expected script_generation completed after retry; got $status2" >&2
  exit 1
fi

echo "[retry-smoke] ok"
