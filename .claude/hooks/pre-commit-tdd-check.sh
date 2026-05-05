#!/bin/bash
# BeWater TDD 强制检查 Hook（增强版）
# 确保测试先于代码提交，并验证时间戳

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 BeWater TDD 检查（增强版）..."

# 获取本次提交的文件
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
  echo "${GREEN}✓ 没有文件需要检查${NC}"
  exit 0
fi

# 检查是否有新的源代码文件（非测试文件）
NEW_CODE_FILES=$(echo "$STAGED_FILES" | grep -E '\.(ts|tsx|js|jsx)$' | grep -v -E '\.test\.|\.spec\.|__tests__|\.config\.|\.d\.ts' || true)

if [ -z "$NEW_CODE_FILES" ]; then
  echo "${GREEN}✓ 没有新的源代码文件${NC}"
  exit 0
fi

# 检查是否有对应的测试文件
HAS_TEST_FILES=$(echo "$STAGED_FILES" | grep -E '\.(test|spec)\.(ts|tsx|js|jsx)$' || true)

if [ -z "$HAS_TEST_FILES" ]; then
  echo "${RED}✗ TDD 检查失败${NC}"
  echo ""
  echo "发现新的源代码文件，但没有对应的测试文件："
  echo "$NEW_CODE_FILES"
  echo ""
  echo "BeWater 要求测试先行（TDD）。请："
  echo "1. 先提交测试文件"
  echo "2. 再提交实现代码"
  echo ""
  echo "如果这是配置文件或文档，可以忽略此检查。"
  echo "如需绕过检查，使用: git commit --no-verify"
  exit 1
fi

# 新增：时间戳验证
echo "⏰ 验证文件创建时间戳..."

VIOLATIONS=0

# 辅助函数：查找测试文件
find_test_file() {
  local code_file="$1"
  local base_name=$(basename "$code_file" | sed 's/\.(ts|tsx|js|jsx)$//')
  local dir_name=$(dirname "$code_file")

  # 尝试多种测试文件命名模式
  local patterns=(
    "${dir_name}/__tests__/${base_name}.test.ts"
    "${dir_name}/__tests__/${base_name}.test.tsx"
    "${dir_name}/${base_name}.test.ts"
    "${dir_name}/${base_name}.test.tsx"
    "${dir_name}/__tests__/${base_name}.spec.ts"
    "${dir_name}/${base_name}.spec.ts"
  )

  for pattern in "${patterns[@]}"; do
    if [ -f "$pattern" ]; then
      echo "$pattern"
      return 0
    fi
  done

  return 1
}

# 检查每个代码文件
for CODE_FILE in $NEW_CODE_FILES; do
  # 查找对应的测试文件
  TEST_FILE=$(find_test_file "$CODE_FILE")

  if [ -z "$TEST_FILE" ]; then
    echo "${YELLOW}⚠️  找不到 $CODE_FILE 的测试文件，跳过时间戳检查${NC}"
    continue
  fi

  # 获取 Git 中的首次提交时间（如果文件已存在）
  CODE_TIME=$(git log --diff-filter=A --format=%at --follow -- "$CODE_FILE" 2>/dev/null | tail -1)
  TEST_TIME=$(git log --diff-filter=A --format=%at --follow -- "$TEST_FILE" 2>/dev/null | tail -1)

  # 如果是新文件（没有 Git 历史），检查文件系统时间戳
  if [ -z "$CODE_TIME" ]; then
    CODE_TIME=$(stat -f %m "$CODE_FILE" 2>/dev/null || stat -c %Y "$CODE_FILE" 2>/dev/null)
  fi

  if [ -z "$TEST_TIME" ]; then
    TEST_TIME=$(stat -f %m "$TEST_FILE" 2>/dev/null || stat -c %Y "$TEST_FILE" 2>/dev/null)
  fi

  # 验证时间戳
  if [ -n "$CODE_TIME" ] && [ -n "$TEST_TIME" ]; then
    if [ "$TEST_TIME" -gt "$CODE_TIME" ]; then
      echo "${RED}✗ TDD 违规：$CODE_FILE${NC}"
      echo "   测试文件: $TEST_FILE"

      # 格式化时间显示
      if command -v date >/dev/null 2>&1; then
        CODE_DATE=$(date -r "$CODE_TIME" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -d "@$CODE_TIME" "+%Y-%m-%d %H:%M:%S" 2>/dev/null)
        TEST_DATE=$(date -r "$TEST_TIME" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -d "@$TEST_TIME" "+%Y-%m-%d %H:%M:%S" 2>/dev/null)

        echo "   实现文件创建: $CODE_DATE"
        echo "   测试文件创建: $TEST_DATE"
      fi

      DELAY=$((TEST_TIME - CODE_TIME))
      echo "   ❌ 测试晚于实现 $DELAY 秒"
      echo ""

      VIOLATIONS=$((VIOLATIONS + 1))
    else
      DELAY=$((CODE_TIME - TEST_TIME))
      echo "${GREEN}✓ $CODE_FILE - 测试先行 (早 $DELAY 秒)${NC}"
    fi
  fi
done

# 如果有违规，阻止提交
if [ $VIOLATIONS -gt 0 ]; then
  echo ""
  echo "${RED}========================================${NC}"
  echo "${RED}TDD 时间戳验证失败：发现 $VIOLATIONS 个违规${NC}"
  echo "${RED}========================================${NC}"
  echo ""
  echo "BeWater 要求测试必须早于实现代码创建。"
  echo ""
  echo "修复方法："
  echo "1. 撤销当前提交"
  echo "2. 先提交测试文件"
  echo "3. 再提交实现文件"
  echo ""
  echo "或者在 tasks.md 中记录 TDD 执行过程后重新提交。"
  echo ""
  echo "如需绕过检查，使用: git commit --no-verify"
  exit 1
fi

echo "${GREEN}✓ TDD 检查通过（包含时间戳验证）${NC}"
exit 0
