#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "$SCRIPT_DIR/_common.sh"

echo "[smoke] create task"
create_resp="$(curl -sS -X POST "$BASE_URL/api/video-tasks" \
  -H 'content-type: application/json' \
  -d '{"input_kind":"topic","input_text":"hello","source_links":["https://example.com/a.mp4"]}')"
echo "$create_resp"
task_id="$(json_get task_id "$create_resp")"

echo "[smoke] get task detail: $task_id"
detail_resp="$(curl -sS "$BASE_URL/api/video-tasks/$task_id")"
echo "$detail_resp"

echo "[smoke] list artifacts: $task_id"
art_resp="$(curl -sS "$BASE_URL/api/video-tasks/$task_id/artifacts")"
echo "$art_resp"

count="$(python3 -c "import json,sys; j=json.loads(sys.argv[1]); print(len(j.get('artifacts', [])))" "$art_resp")"
if [ "$count" -lt 1 ]; then
  echo "expected >=1 artifact, got $count" >&2
  exit 1
fi

echo "[smoke] ok"
