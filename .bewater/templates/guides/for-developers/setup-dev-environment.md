# 开发环境搭建

> 面向贡献 BeWater 方法论与模板的开发者。

## 基础要求

- Node.js 18+
- Python 3.10+
- Git

## 本地准备

1. 克隆仓库并进入目录
2. 确认 `05-implementations/bewater/` 存在
3. 如需验证安装链，准备一个空白测试仓库

## 推荐检查动作

- 运行 `.claude/scripts/check-doc-consistency.sh`
- 检查 `.claude/skills/` 与 `WORKFLOW.md` 是否同一套状态机
- 检查 `.claude/agents/` 与 Skill 调用路径是否一致
- 检查 `templates/` 与 `install.sh` 的安装面是否一致

## 提交前自检

- 新增文档是否有断链
- 是否引入旧术语（如旧预发布阶段名、旧 review artifact 字段）
- 是否引入旧路径写法（如裸路径而非 `.claude/skills/`、`.claude/agents/`）
- 安装后能否通过 `./.claude/scripts/bewater-doctor.sh`
