#!/bin/bash

# BeWater Frontmatter 验证脚本
# 检查 .claude/skills 和 .claude/agents 的 frontmatter 字段是否完整

set -e

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
claude_dir="$(cd "$script_dir/.." && pwd)"
skills_dir="$claude_dir/skills"
agents_dir="$claude_dir/agents"

echo "🔍 BeWater Frontmatter 验证"
echo "=============================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 计数器
total_errors=0
total_warnings=0

# 验证 Skills
echo "📋 验证 Skills..."
echo ""

for skill_dir in "$skills_dir"/*/; do
    [ -d "$skill_dir" ] || continue

    skill_file="${skill_dir}SKILL.md"

    if [ ! -f "$skill_file" ]; then
        echo -e "${RED}❌ 文件不存在: $skill_file${NC}"
        ((total_errors++))
        continue
    fi

    skill_name=$(basename "$skill_dir")
    echo "检查 $skill_name..."

    # Claude 官方必需字段
    required_fields=("name" "description")
    for field in "${required_fields[@]}"; do
        if ! grep -q "^${field}:" "$skill_file"; then
            echo -e "  ${RED}❌ 缺少必需字段: $field${NC}"
            ((total_errors++))
        fi
    done

    # BeWater 标准推荐字段
    recommended_fields=("allowed-tools" "user-invocable" "context" "effort")
    for field in "${recommended_fields[@]}"; do
        if ! grep -q "^${field}:" "$skill_file"; then
            echo -e "  ${YELLOW}⚠️  缺少推荐字段: $field${NC}"
            ((total_warnings++))
        fi
    done

    # 常用可选字段
    optional_fields=("argument-hint" "model" "when-to-use" "visibility")
    for field in "${optional_fields[@]}"; do
        if ! grep -q "^${field}:" "$skill_file"; then
            echo -e "  ${YELLOW}ℹ️  未设置可选字段: $field${NC}"
        fi
    done

    echo ""
done

# 验证 Agents
echo "🤖 验证 Agents..."
echo ""

for agent_file in "$agents_dir"/*.md; do
    [ -f "$agent_file" ] || continue

    agent_name=$(basename "$agent_file" .md)
    echo "检查 $agent_name..."

    # 必需字段
    required_fields=("name" "agentType" "description" "role" "phase" "tools")
    for field in "${required_fields[@]}"; do
        if ! grep -q "^${field}:" "$agent_file"; then
            echo -e "  ${RED}❌ 缺少必需字段: $field${NC}"
            ((total_errors++))
        fi
    done

    # 可选但推荐的字段
    recommended_fields=("whenToUse" "effort" "color")
    for field in "${recommended_fields[@]}"; do
        if ! grep -q "^${field}:" "$agent_file"; then
            echo -e "  ${YELLOW}⚠️  缺少推荐字段: $field${NC}"
            ((total_warnings++))
        fi
    done

    echo ""
done

# 总结
echo "=============================="
echo "验证完成"
echo ""

if [ $total_errors -eq 0 ] && [ $total_warnings -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过！${NC}"
    exit 0
elif [ $total_errors -eq 0 ]; then
    echo -e "${YELLOW}⚠️  发现 $total_warnings 个警告${NC}"
    exit 0
else
    echo -e "${RED}❌ 发现 $total_errors 个错误和 $total_warnings 个警告${NC}"
    exit 1
fi
