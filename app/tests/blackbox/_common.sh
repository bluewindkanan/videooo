#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "missing command: $1" >&2; exit 127; }
}

require_cmd curl
require_cmd python3

json_get() {
  local path="$1"
  local json_text="$2"
  python3 -c 'import json,sys; from functools import reduce; data=reduce(lambda d,p: d[int(p)] if p.isdigit() else d[p], sys.argv[1].split("."), json.loads(sys.argv[2])); print(data)' "$path" "$json_text"
}
