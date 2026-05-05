# Architecture（架构约束）

> **用途**: 定义架构约束和技术选型，适用于复杂功能或高风险系统
> **使用场景**: 当功能涉及多个模块、需要明确技术栈、或有架构风险时启用

## 架构概览

**架构风格**: [单体/微服务/Serverless/...]

**核心原则**:
- 原则 1: [描述]
- 原则 2: [描述]
- 原则 3: [描述]

## 技术栈

### 前端
- **框架**: [React/Vue/Angular/...]
- **状态管理**: [Redux/Zustand/...]
- **UI 库**: [Ant Design/Material-UI/...]
- **构建工具**: [Vite/Webpack/...]

### 后端
- **语言**: [Node.js/Python/Go/Java/...]
- **框架**: [Express/FastAPI/Gin/Spring Boot/...]
- **数据库**: [PostgreSQL/MySQL/MongoDB/...]
- **缓存**: [Redis/Memcached/...]

### 基础设施
- **部署**: [Docker/K8s/Serverless/...]
- **CI/CD**: [GitHub Actions/GitLab CI/...]
- **监控**: [Prometheus/Grafana/...]

## 模块划分

> 路径约束：应用代码路径必须与 `.bewater/install-meta.json` 的 `application_root` 对齐。当 `application_root=app` 时，目录结构应写成 `app/src/...`，或明确注明“以下路径相对于 application_root（app/）”。

```
┌─────────────────────────────────────┐
│         Presentation Layer          │
│  (UI Components, Pages, Routes)     │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│         Application Layer           │
│  (Business Logic, Use Cases)        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│          Domain Layer               │
│  (Entities, Value Objects)          │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│       Infrastructure Layer          │
│  (Database, External APIs)          │
└─────────────────────────────────────┘
```

## 关键约束

### 性能约束
- 响应时间: < [X]ms
- 并发支持: ≥ [N] 用户
- 数据库查询: < [X]ms

### 安全约束
- 认证方式: [JWT/Session/OAuth/...]
- 授权模型: [RBAC/ABAC/...]
- 数据加密: [AES-256/RSA/...]

### 可扩展性约束
- 水平扩展: [支持/不支持]
- 垂直扩展: [支持/不支持]
- 缓存策略: [描述]

### 可维护性约束
- 代码规范: [ESLint/Prettier/...]
- 测试覆盖率: ≥ [X]%
- 文档要求: [描述]

## 数据模型

### 核心实体

**Entity 1: [名称]**
```
{
  id: string
  field1: type
  field2: type
  createdAt: timestamp
  updatedAt: timestamp
}
```

**Entity 2: [名称]**
```
{
  id: string
  field1: type
  field2: type
}
```

### 关系图

```
Entity1 (1) ──── (N) Entity2
Entity2 (N) ──── (N) Entity3
```

## API 设计

### RESTful API

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | /api/resource | 获取列表 | - | Array |
| POST | /api/resource | 创建资源 | Object | Object |
| PUT | /api/resource/:id | 更新资源 | Object | Object |
| DELETE | /api/resource/:id | 删除资源 | - | Status |

### GraphQL API（如适用）

```graphql
type Query {
  resource(id: ID!): Resource
  resources: [Resource!]!
}

type Mutation {
  createResource(input: ResourceInput!): Resource!
  updateResource(id: ID!, input: ResourceInput!): Resource!
  deleteResource(id: ID!): Boolean!
}
```

## API 命名约定（必填）

> ⚠️ 前后端字段命名必须在项目初始化时统一，避免后续跨端映射混乱

**命名风格**: [camelCase / snake_case]

**规则**:
- 数据库字段: [snake_case / camelCase]
- API 请求/响应: [snake_case / camelCase]
- 前端代码: [camelCase / snake_case]
- 如果前后端风格不同，必须在 API 层定义统一的字段映射函数

**示例**:
```
// 如果选择 camelCase
GET /api/topics → { "productName": "...", "createdAt": "..." }

// 如果选择 snake_case
GET /api/topics → { "product_name": "...", "created_at": "..." }
```

## 并发约束（如适用）

> 适用于涉及下载、批量请求、外部 API 调用的项目

- **下载并发数**: [N]（同时下载的最大数量）
- **搜索并发数**: [N]（同时搜索的平台数）
- **API 请求并发数**: [N]
- **实现方式**: [asyncio.Semaphore / Promise.all 限制 / 队列]

## 部署架构

```
┌─────────────┐
│   CDN       │
└──────┬──────┘
       │
┌──────▼──────┐
│  Load       │
│  Balancer   │
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
┌──▼──┐ ┌──▼──┐
│ App │ │ App │
│ 1   │ │ 2   │
└──┬──┘ └──┬──┘
   │       │
   └───┬───┘
       │
┌──────▼──────┐
│  Database   │
│  (Primary)  │
└─────────────┘
```

## 风险与权衡

### 技术风险
- [ ] 风险 1: [描述] - 缓解措施: [...]
- [ ] 风险 2: [描述] - 缓解措施: [...]

### 技术债务
- [ ] 债务 1: [描述] - 偿还计划: [...]
- [ ] 债务 2: [描述] - 偿还计划: [...]

### 权衡决策
- **决策 1**: [描述] - 选择 [A] 而非 [B]，因为 [原因]
- **决策 2**: [描述] - 选择 [A] 而非 [B]，因为 [原因]
