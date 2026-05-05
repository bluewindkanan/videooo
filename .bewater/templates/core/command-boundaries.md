# BeWater 命令职责边界

版本: 4.0.0 | 日期: 2026-04-04

## 核心原则

### 1. 状态推进必须证据驱动
- `/bewater-build` 生产实现与 review 证据
- `/bewater-validate` 生产验证证据
- `/bewater-ship` 只消费并核验 validate 证据，不能凭口头判断推进状态

### 2. 单一职责
- `state.json` = 唯一权威状态
- `context-manifest.md` = 摘要索引
- `session-context.md` = 会话缓存

### 3. 主代理与子代理分工
- 主代理：调度、核验、状态回写
- Builder：实现代码、测试、回执
- Reviewer：审查与 blocker 判定
- QA：验证与 `validation-report.md`

---

## /bewater-build - 开发阶段

### 核心职责

Builder Agent 执行实现，主代理只做调度与核验。

### 包含内容
1. ✅ TDD 实现（RED → GREEN → REFACTOR）
2. ✅ 单元/集成/E2E 自动化测试资产
3. ✅ Builder 回执输出
4. ✅ 增量/最终 review 触发
5. ✅ 关键文件存在性核验
6. ✅ 关键编译/测试检查
7. ✅ `shared_api_changed=true` 时全量回归

### 不包含
- ❌ QA 场景验证
- ❌ 安全/性能验证
- ❌ 发布决策
- ❌ 用临时手工验证替代应提交的 E2E 测试代码

### Builder 回执最小字段
- `files_verified`
- `callsites_checked`
- `shared_api_changed`
- `type_escape_used`
- `write_edit_permission_denied`

### build 阻断条件
- 使用新增 `as any` / 类型逃逸
- 修改 Props / 共享 API 但未同步调用点
- 已有工具函数可复用却局部重复实现
- Builder 声称完成但关键文件未落盘且 1 次重试后仍失败
- Write/Edit 权限失败（主代理直接 fallback，不重试）
- `shared_api_changed=true` 但未执行全量回归

---

## /bewater-validate - 验证阶段

### 核心职责

生成可审计 `validation-report.md`，为 ship 提供真实证据。

### 包含内容
1. ✅ AC 覆盖验证
2. ✅ 执行命令与结果记录
3. ✅ 运行并审计 Build 阶段提交的 E2E 套件
4. ✅ Spec consistency 四项检查
5. ✅ blocker 分级（P0/P1/P2/P3）
6. ✅ `release_decision: go|no-go`

### 不包含
- ❌ 代码实现
- ❌ 临时补写正式 E2E 测试代码
- ❌ 以 review 替代验证
- ❌ 直接写入 `shipped`

---

## /bewater-ship - 发布阶段

### 核心职责

消费 validate 证据并执行发布，不重新发明 gate。

Ship grain: `/bewater-ship` operates on a validated feature/slice. Build batches are internal implementation units and must not be treated as shipped user-facing releases; not every batch should trigger ship.

### 进入条件
1. `current_state=building`
2. `review_gate.status=passed`
3. `ship_precheck_gate.status=go`
4. `validation-report.md` 存在且内容完整

Gate ownership: validate-flow writes `validation_outcome`; ship-flow writes `ship_precheck_gate`.

### 必做核验
- `release_decision: go`
- E2E 结果存在
- Spec consistency 结果存在
- `evidence_checked=true` 仅在 ship 核验完成后写入

### 禁止事项
- ❌ 无 report 直接 shipped
- ❌ report 缺失关键段落仍 shipped
- ❌ 以“刚跑过 validate”替代 artifact 校验

---

## 典型工作流

```text
/bewater-build
  ↓ 代码 + 测试 + review 证据
/bewater-ship
  ↓ validation-report.md + validation_outcome
  ↓ ship-flow synthesizes ship_precheck_gate=go|no-go
  ↓ 核验 validation-report.md
  ↓ 满足证据条件才进入 shipped
```

---

## 边界对比表

| 维度 | /bewater-build | /bewater-validate | /bewater-ship |
|------|----------------|-------------------|---------------|
| 目标 | 实现正确 | 验证正确 | 消费证据并发布 |
| 执行者 | 主代理调度 + Builder/Reviewer | 主代理调度 + QA | 主代理 |
| 主要产物 | 代码、测试、review 结果、Builder 回执 | validation-report.md | release record |
| 是否能推进 shipped | 否 | 否 | 仅在证据核验通过时可 |
| 核心失败信号 | 文件未落盘、回执不完整、review blocker | QA blocker、E2E 缺失、Spec inconsistent | 证据缺失、gate 非 go |

---

## 相关文档

- `state-machine.md`
- `state.json`
- `spec-consistency-checklist.md`
- `risk-assessment.md`

## vNext Gate Writing Rules

- `/bewater-plan` writes `prebuild_review_gate`
- `/bewater-build` writes `review_gate`
- `/bewater-ship` writes `ship_precheck_gate`
- `release_execution_failure` keeps release readiness in `building.ready_to_ship`
- stale gates come from digest / artifact drift, not from infra failure alone
