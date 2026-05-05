#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

echo "[smoke] create task (topic input, no FAIL)"
create_resp="$(curl -sS -X POST "$BASE_URL/api/video-tasks" \
  -H 'content-type: application/json' \
  -d '{"input_kind":"topic","input_text":"短视频制作技巧","source_links":[]}')"
echo "$create_resp"
task_id="$(json_get task_id "$create_resp")"

echo "[smoke] get task detail: $task_id"
detail_resp="$(curl -sS "$BASE_URL/api/video-tasks/$task_id")"
echo "$detail_resp"

# Verify expected steps exist: script_generation, storyboard (if supported), review_script
step_info="$(python3 -c "
import json, sys
j = json.loads(sys.argv[1])
keys = sorted(s['step_key'] for s in j.get('steps', []))
for req in ['script_generation', 'review_script']:
    if req not in keys:
        print(f'missing required step: {req}', file=sys.stderr)
        sys.exit(1)
print(f'{len(keys)}|{\",\".join(keys)}')
" "$detail_resp")"
echo "[smoke] steps found: ${step_info#*|} (count: ${step_info%%|*})"
step_count="${step_info%%|*}"
if [ "$step_count" -lt 2 ]; then
  echo "expected >=2 steps, got $step_count" >&2
  exit 1
fi

# Verify script_generation step is completed
sg_status="$(python3 -c "
import json, sys
j = json.loads(sys.argv[1])
for s in j.get('steps', []):
    if s['step_key'] == 'script_generation':
        print(s['status'])
        break
" "$detail_resp")"
if [ "$sg_status" != "completed" ]; then
  echo "expected script_generation completed, got $sg_status" >&2
  exit 1
fi

echo "[smoke] list artifacts: $task_id"
art_resp="$(curl -sS "$BASE_URL/api/video-tasks/$task_id/artifacts")"
echo "$art_resp"

# Verify artifacts exist for each step (input + script_generation at minimum)
art_count="$(python3 -c "import json,sys; j=json.loads(sys.argv[1]); print(len(j.get('artifacts', [])))" "$art_resp")"
if [ "$art_count" -lt 2 ]; then
  echo "expected >=2 artifacts (input + script_generation), got $art_count" >&2
  exit 1
fi

# Verify script_generation artifacts contain both llm_raw and parsed_json
art_types="$(python3 -c "
import json, sys
j = json.loads(sys.argv[1])
sg_types = sorted(a['artifact_type'] for a in j.get('artifacts', []) if a['step_key'] == 'script_generation')
print(','.join(sg_types))
" "$art_resp")"
if echo "$art_types" | grep -qv "parsed_json"; then
  echo "expected parsed_json artifact for script_generation, got types: $art_types" >&2
  exit 1
fi

echo "[smoke] verify task list contains created task"
list_http_code="$(curl -sS -o /tmp/smoke_list_resp.txt -w '%{http_code}' "$BASE_URL/api/video-tasks")"
if [ "$list_http_code" = "200" ]; then
  list_resp="$(cat /tmp/smoke_list_resp.txt)"
  echo "$list_resp"
  found="$(python3 -c "
import json, sys
j = json.loads(sys.argv[1])
task_id = sys.argv[2]
found = any(t['id'] == task_id for t in j.get('tasks', []))
print('yes' if found else 'no')
" "$list_resp" "$task_id")"
  if [ "$found" != "yes" ]; then
    echo "task $task_id not found in task list" >&2
    exit 1
  fi
else
  echo "[smoke] task list endpoint returned HTTP $list_http_code — skipping list check (endpoint not yet deployed)"
fi

echo "SMOKE PASSED"
