#!/usr/bin/env bash
# PostToolUse hook: suggest next skill after a BeWater skill completes
# Reads JSON from stdin, extracts tool_input.skill, outputs next-step suggestion

# Read JSON from stdin
input=$(cat)

# Extract skill name from tool_input.skill (grep || true to avoid pipefail on no match)
skill=$(echo "$input" | { grep -o '"skill"[[:space:]]*:[[:space:]]*"[^"]*"' || true; } | head -1 | sed 's/.*"skill"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

# Extract args (optional, for skill chaining with feature number)
args=$(echo "$input" | { grep -o '"args"[[:space:]]*:[[:space:]]*"[^"]*"' || true; } | head -1 | sed 's/.*"args"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

# Chain mapping: completed skill → suggested next step
case "${skill:-}" in
  bewater-init)
    echo "💡 BeWater 链式提示: 项目初始化完成，请先确认首个功能候选；确认后执行 /bewater-goal 创建功能目标"
    ;;
  bewater-goal)
    echo "💡 BeWater 链式提示: 目标定义完成且需求已确认，下一步执行 /bewater-plan${args:+ $args} 生成任务清单"
    ;;
  bewater-architect)
    echo "💡 BeWater 链式提示: 架构设计完成，建议执行 /bewater-plan${args:+ $args} 生成任务清单"
    ;;
  bewater-plan)
    echo "💡 BeWater 链式提示: 任务规划完成，建议执行 /bewater-build${args:+ $args} 开始代码实现"
    ;;
  bewater-build)
    echo "💡 BeWater 链式提示: 代码实现完成，建议执行 /bewater-validate${args:+ $args} 生成验证证据"
    ;;
  bewater-validate)
    echo "💡 BeWater 链式提示: 验证完成，建议执行 /bewater-ship${args:+ $args} 发布功能"
    ;;
  bewater-ship)
    echo "💡 BeWater 链式提示: 功能已发布，建议执行 /bewater-learn${args:+ $args} 提取可复用模式"
    ;;
esac

exit 0
