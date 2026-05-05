#!/bin/bash
# BeWater 文档完整性检查 Hook
# 三层检查：
#   层 0 — 项目层：docs/00-project/vision.md + architecture.md 存在且已填写
#   层 1 — 功能层：最新 01-features 下 feature.md + tasks.md 存在
#   层 2 — 内容层：feature.md 内容充实，tasks.md 有任务条目

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "📋 BeWater 文档完整性检查..."

# ============================================================
# 层 0: 项目层文档检查（00-project）
# ============================================================
echo ""
echo "🔍 层 0: 项目层文档检查..."

check_project_doc() {
  local doc="$1"
  local doc_name="$2"

  if [ ! -f "$doc" ]; then
    echo -e "${RED}✗ 缺少项目文档: $doc${NC}"
    echo ""
    echo "  BeWater 要求在开始功能开发前，先完成项目初始化。"
    echo "  请运行 /bewater-init 并完成对话式引导，生成 $doc_name"
    echo ""
    return 1
  fi

  # 检测未替换的占位符。忽略 Markdown checkbox、动态路由和链接文本。
  local placeholder_count
  placeholder_count=$(python3 - "$doc" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = re.sub(r"```.*?```", "", text, flags=re.S)
markers = {
    "...",
    "x",
    "n",
    "描述",
    "说明",
    "名称",
    "标题",
    "姓名",
    "姓名/团队",
    "决策编号",
    "决策标题",
    "决策者",
    "变更描述",
    "修正案描述",
    "是/否",
    "对后续功能的影响",
    "为什么需要这次更新",
}
count = 0
for match in re.finditer(r"\[([^\]]*)\]", text):
    content = match.group(1).strip()
    if content in {"", " ", "x", "X"}:
        continue
    if match.end() < len(text) and text[match.end()] == "(":
        continue
    if content.startswith("...") and len(content) > 3:
        continue
    normalized = content.lower()
    if normalized in markers or normalized.startswith("todo") or normalized.startswith("tbd"):
        count += 1
        continue
    if any(word in content for word in ("描述", "说明", "姓名", "编号", "标题")):
        count += 1
print(count)
PY
)

  if [ "$placeholder_count" -gt 5 ]; then
    echo -e "${RED}✗ $doc 尚未填写（检测到 $placeholder_count 个未替换占位符）${NC}"
    echo ""
    echo "  文件内容仍为模板状态，请运行 /bewater-init 完成对话式填写。"
    echo ""
    return 1
  fi

  echo -e "${GREEN}✓ ${doc}（占位符 ${placeholder_count} 个）${NC}"
  return 0
}

PROJECT_OK=true
check_project_doc "docs/00-project/vision.md" "产品愿景文档" || PROJECT_OK=false
check_project_doc "docs/00-project/architecture.md" "技术架构约束文档" || PROJECT_OK=false
check_project_doc "docs/00-project/decision-log.md" "决策记录文档" || PROJECT_OK=false

if [ "$PROJECT_OK" = false ]; then
  echo -e "${RED}✗ 层 0 检查失败 — 项目层文档不完整${NC}"
  echo ""
  echo "  解决方案："
  echo "    1. 运行 /bewater-init 完成项目初始化"
  echo "    2. 完成产品愿景（vision.md）和技术约束（architecture.md）对话"
  echo "    3. 再运行 /bewater-build"
  exit 1
fi

echo ""
echo "🔍 层 1: 功能层文档检查..."

# 动态检测 docs/01-features/ 下最新功能目录
FEATURES_DIR="docs/01-features"
LATEST_FEATURE=""

if [ -d "$FEATURES_DIR" ]; then
  LATEST_FEATURE=$(ls -d "$FEATURES_DIR"/[0-9]* 2>/dev/null | sort | tail -1)
fi

if [ -z "$LATEST_FEATURE" ]; then
  echo "${RED}✗ 文档完整性检查失败${NC}"
  echo ""
  echo "在 $FEATURES_DIR/ 下没有找到任何功能目录。"
  echo ""
  echo "BeWater 要求文档驱动开发。请先创建功能文档："
  echo ""
  echo "1. 运行 /bewater-goal 定义功能目标（自动生成 feature.md）"
  echo "2. 运行 /bewater-plan 生成任务清单（自动生成 tasks.md）"
  echo ""
  echo "然后再开始编写代码。"
  exit 1
fi

# 检查最新功能目录下的必需文档
REQUIRED_DOCS=(
  "$LATEST_FEATURE/feature.md"
  "$LATEST_FEATURE/tasks.md"
)

MISSING_DOCS=()

for doc in "${REQUIRED_DOCS[@]}"; do
  if [ ! -f "$doc" ]; then
    MISSING_DOCS+=("$doc")
  fi
done

if [ ${#MISSING_DOCS[@]} -gt 0 ]; then
  echo "${RED}✗ 文档完整性检查失败${NC}"
  echo ""
  echo "在最新功能目录 $(basename "$LATEST_FEATURE") 下缺少必需的文档："
  for doc in "${MISSING_DOCS[@]}"; do
    echo "  - $doc"
  done
  echo ""
  echo "BeWater 要求文档驱动开发。请先创建这些文档："
  echo ""
  echo "1. 运行 /bewater-goal 创建 feature.md"
  echo "2. 运行 /bewater-plan 创建 tasks.md"
  echo ""
  echo "然后再开始编写代码。"
  exit 1
fi

# 检查 feature.md 是否为空或只有模板
if [ -f "$LATEST_FEATURE/feature.md" ]; then
  FEATURE_CONTENT=$(grep -v '^#' "$LATEST_FEATURE/feature.md" | grep -v '^$' | grep -v '^<!--' | wc -l)
  if [ "$FEATURE_CONTENT" -lt 5 ]; then
    echo "${YELLOW}⚠ feature.md 内容过少，可能未填写完整${NC}"
  fi
fi

# 检查 tasks.md 的 execution contract（ready task 必须具备完整 Execution Block）
if [ -f "$LATEST_FEATURE/tasks.md" ]; then
  TASKS_PATH="$LATEST_FEATURE/tasks.md"
  python3 ".claude/scripts/check-task-execution-readiness.py" --tasks "$TASKS_PATH"
fi

echo -e "${GREEN}✓ 层 1 通过（功能: $(basename "$LATEST_FEATURE")）${NC}"

echo ""
echo "提示：若功能已进入 building 阶段，请优先运行 /bewater-ship --precheck，而不是直接公开调用 /bewater-validate。"
echo -e "${GREEN}✅ 全部检查通过（层 0 + 层 1 + 层 2）${NC}"
exit 0
