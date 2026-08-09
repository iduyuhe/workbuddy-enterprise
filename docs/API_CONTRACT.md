# WorkBuddy Enterprise Edition — 核心服务接口契约（REST）

> 版本：v1.0 · MVP 阶段 1
> 规范：REST + JSON；鉴权统一 Bearer JWT（由 gateway 校验）；服务间内部调用信任网关注入头 `X-User-Id` / `X-Project-Id`。
> 本文是所有实现团队（后端/前端/AI）的**唯一接口事实来源**。

## 通用约定

- Base URL（对外）：`https://<host>/api`
- 所有请求需 `Authorization: Bearer <jwt>`（登录/令牌接口除外）。
- 错误统一体：`{ "error": { "code": "RBAC_DENIED", "message": "...", "req_id": "..." } }`
- 分页：`?page=1&size=20`，响应含 `{ "items": [], "total": 0, "page": 1, "size": 20 }`。
- 时间统一 ISO-8601 UTC。

---

## 1. 认证授权（auth-service :8002）

### 1.1 OIDC 登录起点
`GET /auth/login?redirect_uri=<url>`
- 302 跳转到企业 IdP 授权端点（OIDC 授权码流）。

### 1.2 回调换 token
`POST /auth/callback`
- body：`{ "code": "...", "state": "..." }`
- 200：`{ "access_token": "...", "refresh_token": "...", "expires_in": 3600, "token_type": "Bearer" }`

### 1.3 本地登录（兜底）
`POST /auth/login/local`
- body：`{ "username": "...", "password": "..." }`
- 200：同上 token 结构。

### 1.4 刷新令牌
`POST /auth/token/refresh`
- body：`{ "refresh_token": "..." }`
- 200：`{ "access_token": "...", "expires_in": 3600 }`

### 1.5 当前用户
`GET /auth/me`
- 200：`{ "id": "uuid", "username": "...", "display_name": "...", "roles": ["admin"], "projects": ["uuid"] }`

### 1.6 RBAC 校验（内部）
`POST /auth/rbac/check`
- body：`{ "user_id": "uuid", "project_id": "uuid|null", "action": "kb:read" }`
- 200：`{ "allowed": true }` / `403 { "allowed": false }`

### 1.7 用户/角色/项目管理（摘录）
- `GET  /users` / `POST /users` / `GET /users/{id}`
- `GET  /roles` / `POST /roles` / `PUT /roles/{id}/permissions`
- `GET  /projects` / `POST /projects` / `POST /projects/{id}/members`

---

## 2. 模型网关（model-gateway :8001）

### 2.1 对话（流式）
`POST /v1/chat`
- 兼容 OpenAI 风格，扩展企业字段。
- body：
```json
{
  "model": "qwen3-235b",
  "messages": [ { "role": "user", "content": "..." } ],
  "stream": true,
  "project_id": "uuid",
  "expert_id": "uuid|null",
  "tools": "auto|none",
  "temperature": 0.7
}
```
- 200：`text/event-stream`，SSE `data: { "id","choices":[{"delta":{"content":"..."}}], "usage":{...} }`
- 网关在内部先聚合 KB 上下文与可用 Skills/MCP 工具描述后转发。

### 2.2 非流式补全
`POST /v1/completions`
- body 同上 `stream:false`；200：`{ "id":"...", "choices":[{"message":{...}}], "usage":{...} }`

### 2.3 列出可用模型
`GET /v1/models`
- 200：`{ "models": [ { "id":"qwen3-235b", "provider":"vllm", "context_window":32768 }, ... ] }`

### 2.4 模型路由/回退配置（admin）
`GET  /admin/routes` / `PUT /admin/routes`
- body：`{ "project_id":"uuid", "prefer":["qwen3-235b","deepseek-v3"], "fallback":"claude" }`

### 2.5 API Key / BYOK 管理
- `POST /admin/keys` `{ "provider":"claude", "scope":"user", "owner_id":"uuid", "secret_ref":"vault://..." }`
- `GET  /admin/keys?owner_id=uuid`

---

## 3. 知识库（knowledge-service :8005）

### 3.1 创建知识库
`POST /kb`
- body：`{ "name":"...", "project_id":"uuid", "embedding":"bge-m3" }`
- 200：`{ "id":"uuid", "collection":"kb_xxxx" }`

### 3.2 文档入库（ingest）
`POST /kb/{kb_id}/ingest`
- multipart：`file`（PDF/Word/图片/表格）→ MinerU 解析 → bge-m3 切片向量 → Qdrant。
- 或 `POST /kb/{kb_id}/ingest/url` `{ "url":"..." }`
- 202：`{ "document_id":"uuid", "status":"parsing" }`
- 查询状态：`GET /kb/{kb_id}/documents/{document_id}` → `{ "status":"indexed", "chunk_count":42 }`

### 3.3 检索（search）
`POST /kb/{kb_id}/search`
- body：`{ "query":"...", "top_k":5, "rerank":true, "score_threshold":0.3 }`
- 200：
```json
{ "results": [
  { "chunk_id":"...", "document_id":"uuid", "score":0.91,
    "content":"...", "meta": { "page":3 } }
] }
```

### 3.4 知识库/文档管理
- `GET  /kb?project_id=uuid`
- `DELETE /kb/{kb_id}`
- `DELETE /kb/{kb_id}/documents/{document_id}`

---

## 4. 技能管理（skills-registry :8003）

> 兼容 Anthropic Skills 文件式规范：每个 Skill 一个目录（含 `SKILL.md` + 资源）。

### 4.1 注册技能
`POST /skills`
- body：`{ "slug":"pdf", "name":"PDF 处理", "storage_path":"/skills/pdf", "project_id":"uuid|null", "is_public":false }`
- 或 `multipart` 上传目录包。
- 200：`{ "id":"uuid", "version":"0.1.0" }`

### 4.2 列出技能
`GET /skills?project_id=uuid&scope=all|mine`
- 200：`{ "items":[ { "id","slug","name","version","is_public" } ], "total":0 }`

### 4.3 获取技能详情
`GET /skills/{id}` → `{ "id","slug","manifest":{...}, "storage_path" }`

### 4.4 调用技能（元数据/触发）
`POST /skills/{id}/invoke`
- body：`{ "project_id":"uuid", "args": { "input":"..." } }`
- 200：`{ "invocation_id":"uuid", "endpoint":"...", "status":"dispatched" }`
- 实际执行由 agent-runtime（阶段 2）或网关编排消费。

### 4.5 版本
`POST /skills/{id}/versions` `{ "manifest":{...} }` → 新版本；`GET /skills/{id}/versions`

---

## 5. MCP 连接器（mcp-connector :8004）

### 5.1 注册 MCP Server
`POST /mcp/servers`
- body：`{ "name":"erp", "transport":"sse", "endpoint":"http://...", "project_id":"uuid", "secret_ref":"vault://..." }`
- 200：`{ "id":"uuid", "status":"active" }`

### 5.2 同步工具清单
`POST /mcp/servers/{id}/sync` → 拉取工具并写入 `mcp_tools`；200：`{ "tools":12 }`

### 5.3 列出工具
`GET /mcp/servers/{id}/tools?project_id=uuid` → `{ "items":[ { "name","schema_json" } ] }`

### 5.4 调用工具
`POST /mcp/servers/{id}/tools/{tool_name}/call`
- body：`{ "project_id":"uuid", "arguments": { ... } }`
- 200：`{ "result": { ... }, "ok": true }`

---

## 6. 审计（audit-service :8006）

### 6.1 写入审计事件（内部/异步）
`POST /audit/events`
- body：
```json
{ "actor_id":"uuid", "actor_name":"...", "project_id":"uuid",
  "action":"chat", "resource":"conv:xxx", "req_id":"uuid",
  "model":"qwen3-235b", "tokens_in":120, "tokens_out":340,
  "ip":"10.0.0.5", "detail": {} }
```
- 200：`{ "id": 12345 }`

### 6.2 查询审计
`GET /audit/events?project_id=uuid&actor_id=uuid&action=chat&from=ISO&to=ISO&page=1&size=20`
- 200：`{ "items":[ ... ], "total":0 }`

### 6.3 导出（auditor/admin）
`GET /audit/export?project_id=uuid&from=ISO&to=ISO` → `text/csv` 下载。

---

## 7. 网关聚合入口（gateway :8000）

前端只对接 gateway，路径前缀映射到上述服务：

| 前端路径 | 后端服务 |
|---|---|
| `/api/auth/*` | auth-service |
| `/api/v1/chat`, `/api/v1/models` | model-gateway |
| `/api/kb/*` | knowledge-service |
| `/api/skills/*` | skills-registry |
| `/api/mcp/*` | mcp-connector |
| `/api/audit/*` | audit-service |

- 网关在每次请求：校验 JWT → RBAC 检查 → 注入 `X-User-Id`/`X-Project-Id` → 转发 → 异步发审计事件。
- 对话流：`POST /api/v1/chat` 触发第 5 节数据流（KB 检索 + 模型流式）。

---

_契约版本随 MVP 演进而更新；任何破坏性变更需同步后端/前端/AI 三方并 bump 版本。_
