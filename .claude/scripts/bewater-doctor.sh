#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"
EXIT_CODE=0
JSON_MODE=false

if [ "${1:-}" = "--json" ]; then
    JSON_MODE=true
fi

print_check() {
    printf '[CHECK] %s\n' "$1"
}

print_ok() {
    printf '[OK] %s\n' "$1"
}

print_warn() {
    printf '[WARN] %s\n' "$1"
}

print_fail() {
    printf '[FAIL] %s\n' "$1"
    EXIT_CODE=1
}

require_path() {
    local path="$1"
    if [ -e "$ROOT_DIR/$path" ]; then
        print_ok "$path"
    else
        print_fail "$path"
    fi
}

if [ "$JSON_MODE" = true ]; then
    python3 - "$ROOT_DIR" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = "installed" if (root / ".bewater/install-meta.json").exists() else "source"
data = {
    "mode": mode,
    "skills_count": len(list((root / ".claude/skills").glob("*/SKILL.md"))),
    "agents_count": len(list((root / ".claude/agents").glob("*.md"))),
    "contracts": {
        "state_schema": str(root / ".bewater/contracts/state.schema.json"),
        "gate_schema": str(root / ".bewater/contracts/gate.schema.json")
    }
}
print(json.dumps(data, ensure_ascii=False))
PY
    exit 0
fi

is_source_mode=false
if [ -f "$ROOT_DIR/install.sh" ] && [ -d "$ROOT_DIR/.bewater/contracts" ] && [ -d "$ROOT_DIR/.claude/skills" ] && [ ! -f "$ROOT_DIR/.bewater/install-meta.json" ]; then
    is_source_mode=true
fi

if [ "$is_source_mode" = true ]; then
    print_check "BeWater source mode"
    print_ok "Source mode detected"
    require_path "install.sh"
    require_path ".bewater/contracts"
    require_path ".claude/skills"
    require_path ".claude/agents"
    require_path "tests/run_tests.py"
    if [ -x "$ROOT_DIR/.claude/scripts/check-doc-consistency.sh" ]; then
        print_check "Doc consistency"
        (cd "$ROOT_DIR/.claude" && ./scripts/check-doc-consistency.sh) || EXIT_CODE=1
    fi
    exit "$EXIT_CODE"
fi

print_check "BeWater install surface"
require_path ".bewater/state.json"
require_path ".bewater/install-meta.json"
require_path ".claude/skills"
require_path ".claude/agents"
require_path ".claude/scripts/check-doc-consistency.sh"

declared_workflow_doc=""
declared_readme_doc=""
declared_app_root=""
declared_app_readme_doc=""
if [ -f "$ROOT_DIR/.bewater/install-meta.json" ]; then
    declared_workflow_doc="$(python3 - "$ROOT_DIR/.bewater/install-meta.json" <<'PY'
import json
import sys
from pathlib import Path

meta_path = Path(sys.argv[1])
try:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
except Exception:
    print("")
else:
    print(data.get("workflow_doc", ""))
PY
)"

    declared_readme_doc="$(python3 - "$ROOT_DIR/.bewater/install-meta.json" <<'PY'
import json
import sys
from pathlib import Path

meta_path = Path(sys.argv[1])
try:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
except Exception:
    print("")
else:
    print(data.get("readme_doc", ""))
PY
)"

    declared_app_root="$(python3 - "$ROOT_DIR/.bewater/install-meta.json" <<'PY'
import json
import sys
from pathlib import Path

meta_path = Path(sys.argv[1])
try:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
except Exception:
    print("")
else:
    print(data.get("application_root", ""))
PY
)"

    declared_app_readme_doc="$(python3 - "$ROOT_DIR/.bewater/install-meta.json" <<'PY'
import json
import sys
from pathlib import Path

meta_path = Path(sys.argv[1])
try:
    data = json.loads(meta_path.read_text(encoding="utf-8"))
except Exception:
    print("")
else:
    print(data.get("app_readme_doc", ""))
PY
)"
fi

if [ -n "$declared_workflow_doc" ]; then
    require_path "$declared_workflow_doc"
elif [ -f "$ROOT_DIR/WORKFLOW.md" ] || [ -f "$ROOT_DIR/.bewater/WORKFLOW.bewater.md" ]; then
    print_ok "workflow doc"
else
    print_fail "workflow doc"
fi

# README install artifact must be declared in install-meta and present on disk.
if [ -n "$declared_readme_doc" ]; then
    require_path "$declared_readme_doc"
else
    print_fail "install-meta.readme_doc"
fi

if [ -n "$declared_app_root" ]; then
    require_path "$declared_app_root"
else
    print_fail "install-meta.application_root"
fi

if [ -n "$declared_app_readme_doc" ]; then
    require_path "$declared_app_readme_doc"
else
    print_fail "install-meta.app_readme_doc"
fi

if [ -x "$ROOT_DIR/.claude/scripts/check-doc-consistency.sh" ]; then
    print_check "Doc consistency"
    (
        cd "$ROOT_DIR/.claude"
        ./scripts/check-doc-consistency.sh
    ) || EXIT_CODE=1
fi

check_application_root_integrity() {
    print_check "Application root integrity"
    if [ -x "$ROOT_DIR/.claude/scripts/bewater-check.py" ]; then
        if python3 "$ROOT_DIR/.claude/scripts/bewater-check.py" root --project-root "$ROOT_DIR" >/dev/null 2>&1; then
            print_ok "application_root matches product file layout"
        else
            print_fail "application_root does not match product file layout (run: python3 .claude/scripts/bewater-check.py root --project-root .)"
        fi
    fi
}

check_application_root_integrity

check_product_tooling_isolation() {
    print_check "Product tooling isolation"

    if [ ! -f "$ROOT_DIR/package.json" ]; then
        print_ok "no package.json; product tooling isolation not applicable"
        return 0
    fi

    if [ -f "$ROOT_DIR/eslint.config.js" ] || [ -f "$ROOT_DIR/.eslintrc" ] || [ -f "$ROOT_DIR/.eslintrc.json" ]; then
        local eslint_config=""
        if [ -f "$ROOT_DIR/eslint.config.js" ]; then
            eslint_config="$ROOT_DIR/eslint.config.js"
        elif [ -f "$ROOT_DIR/.eslintrc.json" ]; then
            eslint_config="$ROOT_DIR/.eslintrc.json"
        else
            eslint_config="$ROOT_DIR/.eslintrc"
        fi

        local eslint_text
        eslint_text="$(cat "$eslint_config")"
        if [[ "$eslint_text" == *".bewater/**"* && "$eslint_text" == *".claude/**"* && "$eslint_text" == *"docs/**"* ]]; then
            print_ok "eslint ignores BeWater assets"
        else
            print_warn "eslint may scan BeWater assets; add ignores for .bewater/**, .claude/**, and docs/**"
        fi
    else
        print_ok "no eslint config detected"
    fi

    if [ -f "$ROOT_DIR/tsconfig.json" ] && [ -f "$ROOT_DIR/vitest.config.ts" ]; then
        local tsconfig_text
        tsconfig_text="$(cat "$ROOT_DIR/tsconfig.json")"
        if [[ "$tsconfig_text" == *"\"tests\""* && "$tsconfig_text" != *"vitest"* ]]; then
            print_warn "tsconfig.json includes tests but does not mention vitest types; split app/test tsconfig or add test globals"
        else
            print_ok "typescript test/build boundary detected"
        fi
    fi
}

check_product_tooling_isolation

exit "$EXIT_CODE"
