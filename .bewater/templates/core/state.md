# State Contract（状态契约）

> BeWater 项目状态文件 | 版本: 4.0.0

---

## 公开状态链

`uninitialized → initialized → specified → planned → building → shipped`

## 状态数据结构

```json
{
  "version": "4.0.0",
  "methodology_version": "4.0.0",
  "current_state": "initialized",
  "previous_state": "uninitialized",
  "project": "项目名称",
  "current_feature": null,
  "feature_context": {
    "complexity_tier": "standard",
    "implementation_mode": "greenfield",
    "existing_implementation_note": null
  },
  "ready_for_build": false,
  "shipped_features": [],
  "initialized_at": "2026-01-01T00:00:00Z",
  "specified_at": null,
  "planned_at": null,
  "building_at": null,
  "shipped_at": null,
  "learned_at": null,
  "internal_stage": null,
  "artifacts": {
    "foundation_review_path": null,
    "prebuild_review_path": null,
    "feature_path": null,
    "design_path": null,
    "tasks_path": null,
    "review_note_path": null,
    "validation_report_path": null,
    "release_record_path": null,
    "validation_evidence_index_path": null,
    "tdd_receipts_dir": null
  },
  "contract_schemas": {
    "state_schema_path": ".bewater/contracts/state.schema.json",
    "gate_schema_path": ".bewater/contracts/gate.schema.json",
    "builder_receipt_schema_path": ".bewater/contracts/builder-receipt.schema.json",
    "tdd_receipt_schema_path": ".bewater/contracts/tdd-receipt.schema.json",
    "validation_evidence_schema_path": ".bewater/contracts/validation-evidence.schema.json"
  },
  "gates": {
    "foundation_gate": {
      "status": "pending",
      "freshness": { "status": "unknown", "checked_at": null, "stale_reasons": [] },
      "concerns": [],
      "blockers": [],
      "evaluated_at": null,
      "evaluated_commit_sha": null,
      "input_digest": "",
      "input_refs": [],
      "input_digests": {},
      "produced_by": "init-flow",
      "evidence_refs": []
    },
    "feature_review_gate": {
      "status": "pending",
      "freshness": {
        "status": "unknown",
        "checked_at": null,
        "stale_reasons": []
      },
      "concerns": [],
      "blockers": [],
      "evaluated_at": null,
      "evaluated_commit_sha": null,
      "input_digest": "",
      "input_refs": [],
      "input_digests": {},
      "produced_by": "goal-flow",
      "evidence_refs": []
    },
    "architect_gate": {
      "status": "pending",
      "freshness": { "status": "unknown", "checked_at": null, "stale_reasons": [] },
      "concerns": [],
      "blockers": [],
      "evaluated_at": null,
      "evaluated_commit_sha": null,
      "input_digest": "",
      "input_refs": [],
      "input_digests": {},
      "produced_by": "goal-flow",
      "evidence_refs": []
    },
    "prebuild_review_gate": {
      "status": "pending",
      "freshness": { "status": "unknown", "checked_at": null, "stale_reasons": [] },
      "concerns": [],
      "blockers": [],
      "evaluated_at": null,
      "evaluated_commit_sha": null,
      "input_digest": "",
      "input_refs": [],
      "input_digests": {},
      "produced_by": "plan-flow",
      "evidence_refs": []
    },
    "review_gate": {
      "status": "pending",
      "freshness": { "status": "unknown", "checked_at": null, "stale_reasons": [] },
      "concerns": [],
      "blockers": [],
      "evaluated_at": null,
      "evaluated_commit_sha": null,
      "input_digest": "",
      "input_refs": [],
      "input_digests": {},
      "produced_by": "build-flow",
      "evidence_refs": []
    },
    "ship_precheck_gate": {
      "status": "pending",
      "freshness": { "status": "unknown", "checked_at": null, "stale_reasons": [] },
      "concerns": [],
      "blockers": [],
      "evaluated_at": null,
      "evaluated_commit_sha": null,
      "input_digest": "",
      "input_refs": [],
      "input_digests": {},
      "produced_by": "ship-flow",
      "evidence_refs": [],
      "evidence_checked": false
    }
  },
  "runtime": {
    "active_flow": null,
    "subphase": null,
    "route_mode": "standard",
    "validation_outcome": null,
    "retry_counters": {
      "auto_repeat_blockers": 0,
      "evidence_refresh_attempts": 0
    },
    "release_intent": null
  },
  "compat": {},
  "state_history": [
    {
      "from": "uninitialized",
      "to": "initialized",
      "timestamp": "2026-01-01T00:00:00Z",
      "trigger": "/bewater-init"
    }
  ],
  "next_command": "/bewater-goal"
}
```

---

## 状态字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | string | BeWater 版本号 |
| `methodology_version` | string | 方法论版本号 |
| `current_state` | string | 当前状态（仅 6 种之一） |
| `previous_state` | string \| null | 前一个状态 |
| `project` | string | 项目名称 |
| `current_feature` | string \| null | 当前功能编号 |
| `feature_context.complexity_tier` | string | 功能复杂度层级 |
| `feature_context.implementation_mode` | string | 功能实现模式（`greenfield` \| `extension` \| `existing_partial` \| `existing_complete`）|
| `feature_context.existing_implementation_note` | string \| null | 已有实现说明 |
| `ready_for_build` | boolean | 当前是否存在至少一组 dispatchable ready tasks（非永久结论） |
| `shipped_features` | string[] | 已发布功能列表 |
| `*_at` | string \| null | 各阶段时间戳 |
| `internal_stage` | string \| null | 当前内部执行提示 |
| `artifacts.*` | string \| null | 关键产物路径指针 |
| `artifacts.release_record_path` | string|null | 当前 feature 的 ship release record 路径 |
| `contract_schemas.*` | string | 运行时契约 schema 路径 |
| `gates.*.status` | string | Gate 状态 |
| `gates.*.blockers[]` | array | Gate 阻断项列表 |
| `gates.ship_precheck_gate.evidence_checked` | boolean | ship 是否已核验 validate 证据 |
| `state_history[]` | array | 状态转换历史 |
| `next_command` | string | 当 `ready_for_build=true` 时通常为 `/bewater-build`，否则应先回到 `/bewater-plan` 补齐 execution contract |

---

## 6 个状态

1. **uninitialized** - 项目未初始化
2. **initialized** - 初始化完成
3. **specified** - 目标已定义
4. **planned** - `tasks.md` 已通过 `tasks_gate`，且当前存在 execution-ready tasks（ready task 具备 `Execution Block`）
5. **building** - 开发中
6. **shipped** - 已发布

---

## 6 个 Gate

| Gate | 初始状态 | 结果枚举 |
|------|---------|---------|
| `feature_review_gate` | `pending` | `passed \| failed \| blocked` |
| `architect_gate` | `pending` | `passed \| failed` |
| `tasks_gate` | `pending` | `passed \| failed \| blocked` |
| `review_gate` | `pending` | `passed \| failed \| blocked` |
| `ship_precheck_gate` | `pending` | `go \| no-go` |
| `quick_gate` | `pending` | `passed \| failed` |

Build completion is evidenced by task readiness, feature-level `receipts.json`, and `review_gate`; BeWater does not persist a separate public `build_gate`.

---

## 权威性约束

- `state.json` = 唯一权威状态
- `context-manifest.md` = 摘要索引，不作为 gate 依据
- `session-context.md` = 会话缓存，不作为状态依据
- `internal_stage` = 执行提示，不作为状态判定依据
- 进入 `shipped` 前，必须满足：
  - `review_gate.status = passed`
  - `ship_precheck_gate.status = go`
  - `artifacts.validation_report_path` 已记录且文件存在
  - `gates.ship_precheck_gate.evidence_checked = true`

---

## 自动更新

此文件由 BeWater 命令自动更新，请勿手动编辑。

- `/bewater-init` → `uninitialized -> initialized`
- `/bewater-goal` → `initialized -> specified`
- `/bewater-plan` → `specified -> planned`（或 gate 失败保持 `specified`）
- `/bewater-build` → `planned -> building`
- `/bewater-validate` → 保持 `building`，写入 `validation_report_path` 与 `validation_outcome`
- Ownership rule: validate-flow writes `validation_outcome`; ship-flow writes `ship_precheck_gate`
- `existing_complete` 例外：`/bewater-validate` 可从 `planned` 进入，但必须先把状态提升到 `building`
- `/bewater-ship` → `building -> shipped`（仅在证据已核验时）
- `/bewater-learn` → 保持 `shipped`
