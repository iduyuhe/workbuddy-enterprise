# WorkBuddy Enterprise Edition

> **On-premise AI Agent Platform for Large Enterprises.**
> 面向大型企业 / 国企 / 央企 / 金融机构 / 信息安全敏感行业的 **私有化部署 AI 智能体平台**。
> 数据不出公司内网；兼容 Claude（Anthropic）/ Codex（OpenAI）/ 国产开源大模型（Qwen3 / DeepSeek）；
> 把企业自己的「技能 / 岗位 / 专家 / 团队」沉淀为可治理、可复用的智能体资产。

[![License](https://img.shields.io/github/license/iduyuhe/workbuddy-enterprise?style=flat-square)](./LICENSE)
[![Stars](https://img.shields.io/github/stars/iduyuhe/workbuddy-enterprise?style=flat-square)](https://github.com/iduyuhe/workbuddy-enterprise/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/iduyuhe/workbuddy-enterprise?style=flat-square)](https://github.com/iduyuhe/workbuddy-enterprise/commits/main)
[![Issues](https://img.shields.io/github/issues/iduyuhe/workbuddy-enterprise?style=flat-square)](https://github.com/iduyuhe/workbuddy-enterprise/issues)
[![CI](https://img.shields.io/github/actions/workflow/status/iduyuhe/workbuddy-enterprise/ci.yml?style=flat-square)](https://github.com/iduyuhe/workbuddy-enterprise/actions)

---

## ✨ 特性

- **🔒 数据不出域** —— 推理、向量、业务元数据全部运行在客户内网；支持私有化大模型（vLLM / SGLang）。
- **🧩 模型无关网关** —— 统一抽象层，同时接入 Claude（Anthropic）、Codex（OpenAI）、Qwen3、DeepSeek；API Key 托管不落明文。
- **📚 企业知识库 RAG** —— 文档解析（MinerU）+ 向量化（bge-m3）+ 向量库（Qdrant）+ 重排，融入企业私有知识。
- **🛠 Skills 注册中心** —— 兼容 Anthropic Skills 文件式规范，把最佳实践沉淀为可复用技能。
- **🔌 MCP 连接器** —— 复用 Model Context Protocol 生态，接入企业现有系统（数据库 / SaaS / 内部 API）。
- **🛡 企业级治理** —— SSO（OIDC）、RBAC、项目级数据隔离、调用级审计日志；预留等保三级 / 内容审核扩展点。
- **📊 可观测** —— Prometheus + Grafana + Langfuse 全链路监控与 LLM 可观测性。

## 🏗 架构

```mermaid
graph LR
  U[用户 / 企业] -->|HTTPS| GW[API 网关 :8000]
  GW -->|鉴权+路由| AUTH[auth-service :8002]
  GW -->|对话| MG[model-gateway :8001]
  GW -->|知识| KB[knowledge-service :8005]
  GW -->|审计| AUD[audit-service :8006]
  MG --> LLM[(vLLM / Claude / Codex)]
  KB --> QD[(Qdrant 向量)]
  KB --> EMB[bge-m3 Embedding]
  GW --> SK[skills-registry :8003]
  GW --> MCP[mcp-connector :8004]
  AUTH --> PG[(PostgreSQL)]
  AUTH --> R[(Redis)
```

| 服务 | 端口 | 职责 |
|---|---|---|
| `gateway` | 8000 | 唯一对外入口，JWT 校验 + 路由转发 + 审计埋点 |
| `auth-service` | 8002 | 认证 / RBAC / 项目隔离 / OIDC |
| `model-gateway` | 8001 | 统一模型接入（Qwen3/DeepSeek/Claude） |
| `knowledge-service` | 8005 | 企业知识库 RAG（解析→切片→向量→检索） |
| `skills-registry` | 8003 | 技能注册中心（兼容 Anthropic Skills） |
| `mcp-connector` | 8004 | MCP 连接器（工具注册 / 同步 / 调用） |
| `audit-service` | 8006 | 调用级审计日志 |
| `frontend` | 3000 | React/TS 控制台（登录 / 对话 / 知识库 / 审计） |

> 完整技术细节见 [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) 与 [`docs/API_CONTRACT.md`](./docs/API_CONTRACT.md)。

## 🚀 快速开始

### 方式一：本地轻量体验（无需 GPU）

适合开发者在笔记本上跑通最小闭环（使用 SQLite + 内存向量降级，不依赖 GPU / Qdrant / PostgreSQL）：

```bash
# 1. 后端依赖
python -m venv .venv && source .venv/Scripts/activate   # Windows
pip install -r src/gateway/requirements.txt              # 各服务同理

# 2. 依次启动 7 个服务（每个开一个终端）
uvicorn app.main:app --port 8002 -d src/auth-service
uvicorn app.main:app --port 8001 -d src/model-gateway
uvicorn app.main:app --port 8006 -d src/audit-service
uvicorn app.main:app --port 8005 -d src/knowledge-service
uvicorn app.main:app --port 8003 -d src/skills-registry
uvicorn app.main:app --port 8004 -d src/mcp-connector
uvicorn app.main:app --port 8000 -d src/gateway

# 3. 前端
cd src/frontend && npm install && npm run dev   # http://localhost:3000
```

默认账号：`admin / admin123`。登录后创建知识库、上传文档、对话（无 GPU 时对话接口会返回明确错误，知识库检索可正常验证）。

### 方式二：生产级私有化部署（Docker Compose）

见 [`src/deploy/README.md`](./src/deploy/README.md)：

```bash
cp src/deploy/.env.example src/deploy/.env
# 将模型权重放到 /models（如 Qwen3-235B-A22B-FP8）
cd src/deploy && docker compose up -d
```

## 📂 目录结构

```
workbuddy-enterprise/
├── docs/                 # 架构设计 + 接口契约（事实来源）
├── src/
│   ├── gateway/          # API 网关
│   ├── auth-service/     # 认证授权 + RBAC
│   ├── model-gateway/    # 模型网关
│   ├── knowledge-service/# 企业知识库 RAG
│   ├── skills-registry/  # 技能注册中心
│   ├── mcp-connector/    # MCP 连接器
│   ├── audit-service/    # 审计服务
│   ├── frontend/         # React/TS 控制台
│   ├── shared/           # 跨服务共享模型
│   └── deploy/           # 私有化部署资产（docker-compose 等）
├── .github/              # CI / Issue / PR 模板
├── LICENSE               # Apache-2.0
├── CHANGELOG.md          # 版本变更
├── CONTRIBUTING.md       # 贡献指南
├── SECURITY.md           # 安全披露政策
└── ROADMAP.md            # 路线图
```

## 🗺 路线图

详见 [`ROADMAP.md`](./ROADMAP.md)。概要：

- **阶段 1（已完成 · v0.1.0）**：MVP 最小闭环 —— 私有化底座 + 7 微服务 + 前端 + RAG 全链路验证。
- **阶段 2**：生产数据层（PostgreSQL/Qdrant 正式接入）、内容审核、Agent 运行时（LangGraph 编排）、Skills/MCP 真实执行。
- **阶段 3**：信创适配（鲲鹏/海光/麒麟/达梦）、等保三级、多租户。
- **阶段 4**：规模交付（千企）、生态市场（技能/连接器交易）。

## 🔐 安全

本平台面向信息安全敏感行业，安全是核心诉求。请阅读 [`SECURITY.md`](./SECURITY.md) 了解漏洞披露流程，以及企业部署的安全基线建议。

## 🤝 贡献

欢迎 Issue、PR 与讨论。开始前请阅读 [`CONTRIBUTING.md`](./CONTRIBUTING.md) 与 [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md)。

## 📄 许可证

[Apache-2.0](./LICENSE)。商业使用、修改、分发均被允许，请保留版权与许可证声明。

---

_由智能体开发团队 `workbuddy-ent-dev` 构建 · 隶属「工业 5.0 产业生态联盟」生态。_
