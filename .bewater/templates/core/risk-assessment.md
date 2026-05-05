# BeWater 风险评估参考

> 独立参考文档，用于指导测试深度和验证范围。不改 Product Agent、不改 feature.md 格式。
>
> **注意**：TDD 覆盖率阈值和 CR 策略的权威定义见 CLAUDE.md "TDD 质量策略" 章节，本文件仅供参考。

---

## 评分规则

| 因子 | 分值 |
|------|------|
| 涉及认证/安全/支付 | +3 |
| 新增数据库 schema | +3 |
| 触及 >10 文件 | +2 |
| 新增 API 端点 | +2 |
| 新页面/新组件 | +1 |
| 修改共享工具函数 | +1 |
| 仅 CSS/样式 | +0 |
| 仅内容/文案 | +0 |

**评级**：
- 0-1 = Low → Quick 流程 + Smoke only
- 2-3 = Medium → 标准流程 + Standard QA
- 4+ = High → 完整流程（含 Full Validate）

## Quick Path Blocked Categories

`/bewater-quick` must not be used when the requested change involves:

- data migration
- security permission changes
- payment or billing behavior
- production release automation
- cross-module refactor
- irreversible operation

If any category matches, use the standard `goal -> plan -> build -> validate -> ship` path.

---

## 测试要求矩阵

| 级别 | TDD | 覆盖率 | Code Review | Validate | 安全检查 | 性能检查 | E2E 范围 |
|------|-----|--------|-------------|----------|---------|---------|---------|
| Critical | 强制 | 80%+ | 全量+二次审查 | 完整QA+对抗性 | 完整OWASP | 负载测试 | 全部（含 auth+checkout） |
| High | 强制 | 70%+ | 全量审查 | 完整QA | OWASP扫描 | 基线检查 | smoke + 核心流程（auth+cart） |
| Medium | 强制 | 60%+ | 抽检50% | 标准QA | 依赖扫描 | Smoke | smoke + guest 流程 |
| Low | 建议 | 50%+ | 可选 | Smoke only | 跳过 | 跳过 | smoke only |

---

## 验证深度配置

### Low（冒烟测试 + 验收场景 + 构建验证）

适用于：静态页面内容修改、CSS 调整、文案更新

检查项：
- [ ] `npm run build` 通过
- [ ] 页面正常渲染（smoke test）
- [ ] 验收场景（feature.md Given-When-Then）基本验证
- [ ] 无 console 错误

目标报告长度：< 80 行

### Medium（Low + 安全扫描 + 代码审查）

适用于：新页面、新组件、共享工具修改

检查项（含 Low 全部）：
- [ ] `npm audit` 无高危
- [ ] 代码审查（抽检 50%）
- [ ] 类型安全（TypeScript strict）
- [ ] 依赖扫描

### High/Critical（全部 7 层验证栈）

适用于：核心功能、安全相关、多模块变更

检查项（含 Medium 全部）：
- [ ] 完整 QA 场景验证
- [ ] 对抗性测试（边界值、异常路径）
- [ ] OWASP Top 10 完整扫描
- [ ] 性能基线检查（Lighthouse）
- [ ] 架构一致性检查

---

## 使用方式

1. **Feature 定义时**：Product Agent 在生成 feature.md 时根据上述规则判断 risk_level
2. **Build 时**：Builder Agent 根据 risk_level 选择覆盖率和 TDD 深度
3. **Validate 时**：QA Agent 根据 risk_level 选择验证深度配置
4. **Quick 流程**：risk_level = Low 的变更可使用 `/bewater-quick` 快捷命令
