# 变更日志 (Changelog)

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 规范，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-08-09

首个公开 MVP 版本（初始开源发布）。

### 新增 (Added)

- **架构与契约**：`docs/ARCHITECTURE.md`（部署拓扑 / 服务划分 / DDL / 数据流 / 安全模型）、`docs/API_CONTRACT.md`（REST 接口事实来源）。
- **私有化部署底座**：`src/deploy/`（docker-compose 编排 vLLM + Qdrant + PostgreSQL + Redis + Langfuse + Prometheus + Grafana，vLLM 启动脚本，监控配置）。
- **7 个后端微服务**（Python / FastAPI）：
  - `gateway`（:8000）API 网关：JWT 校验、路由转发、审计埋点、对话聚合。
  - `auth-service`（:8002）认证授权 + RBAC + 项目级数据隔离 + OIDC 预留。
  - `model-gateway`（:8001）统一模型接入（Qwen3 / DeepSeek / Claude），API Key 托管。
  - `knowledge-service`（:8005）企业知识库 RAG（解析 / 切片 / bge-m3 向量 / Qdrant + InMemory 降级 / 检索重排预留）。
  - `skills-registry`（:8003）技能注册中心（兼容 Anthropic Skills 文件式规范，版本管理）。
  - `mcp-connector`（:8004）MCP 连接器（服务器注册 / 工具同步 / 调用中继）。
  - `audit-service`（:8006）调用级审计日志写入与查询。
- **前端控制台**（React / TS，`src/frontend/`）：登录、对话工作台（SSE 流式）、知识库管理、审计视图、RBAC 角色显隐、路由守卫。
- **共享层** `src/shared/`：跨服务公共错误体 / JWT 载荷 / 分页模型。
- **真实验证报告** `VERIFICATION_REPORT.md`：7 服务实测全通过，RAG 全链路命中。
- **开源配套**：LICENSE（Apache-2.0）、README、CONTRIBUTING、CODE_OF_CONDUCT、SECURITY、ROADMAP、QUICKSTART、CI 与 Issue/PR 模板。

### 已知限制 (Known Limitations)

- 真实 LLM 对话需 GPU / vLLM，验证环境未包含（对话接口在无模型时优雅报错）。
- Qdrant / PostgreSQL 生产数据层以 SQLite / InMemory 降级跑通，正式接入见路线图。
- 内容审核、等保三级、信创适配为后续阶段。
- OIDC 为预留接口，需客户 IdP 配置。

---

## 版本说明

- 类型：`Added` 新功能 / `Changed` 变更 / `Deprecated` 弃用 / `Removed` 移除 / `Fixed` 修复 / `Security` 安全。
- 每次发版打 Git Tag（如 `v0.1.0`）并发布 GitHub Release。
