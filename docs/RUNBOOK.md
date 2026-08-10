# 运维手册 (RUNBOOK)

WorkBuddy Enterprise Edition 本地开发 / 生产启动与排障手册。配套文档：
`README.md` · `ARCHITECTURE.md` · `API_CONTRACT.md` · `QUICKSTART.md` · `ROADMAP.md`。

---

## 1. 环境要求

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | ≥ 3.11（推荐 3.13 managed） | 后端服务运行时 |
| Node.js | ≥ 18（推荐 22） | 前端构建 |
| venv | 任意 | 依赖隔离，建议共享一个 venv 装全部 `requirements.txt` |
| Docker（可选） | — | 生产起 Qdrant / PostgreSQL / Redis；MVP 可用 InMemory + sqlite 降级，免 Docker |

依赖安装（共享 venv 示例）：
```bash
python -m venv .venv
source .venv/Scripts/activate        # Windows
for s in auth-service gateway model-gateway audit-service knowledge-service skills-registry mcp-connector; do
  pip install -r src/$s/requirements.txt
done
```

---

## 2. 服务与端口

| 服务 | 端口 | 职责 |
|---|---|---|
| gateway | 8000 | API 网关，前端唯一入口，代理 + 鉴权 + 审计埋点 |
| model-gateway | 8001 | 模型路由（vLLM / SGLang / Claude），OpenAI 兼容 `/v1/chat/completions` |
| auth-service | 8002 | 本地登录 / OIDC / JWT / RBAC |
| skills-registry | 8003 | 技能注册与检索 |
| mcp-connector | 8004 | MCP 连接器管理 |
| knowledge-service | 8005 | 企业知识库 RAG（解析→切片→向量→检索） |
| audit-service | 8006 | 审计事件写入与查询（内部接口，仅网关可调用） |
| agent-service | 8007 | Agent 运行时（LangGraph ReAct：RAG / 技能 / MCP 真实编排） |

各服务独立启动。由于代码跨服务共享 `src/shared` 包，启动时必须让 `src` 在 `PYTHONPATH` 上（否则 `from shared...` 会 ImportError）。推荐在 `src/<service>` 目录内启动并把仓库 `src` 加入 `PYTHONPATH`：

```bash
# 以 knowledge-service 为例（agent-service / gateway 等同理）
cd src/knowledge-service
PYTHONPATH=/绝对路径/enterprise-platform-plan/src uvicorn app.main:app --port 8005
```

> 注意：仓库内每个服务自身的 `app` 包位于 `src/<service>/app`，`cd` 进服务目录后 `app` 可解析；`shared` 需靠 `PYTHONPATH=src` 解析。两者同时具备才能正常启动。

前端只对接 gateway `:8000`；开发期 vite 代理 `/api` → `:8000`，生产由 nginx 反代。

---

## 3. 端口清理（Windows 必读）

Git Bash 下 `taskkill` 常杀不掉 Windows 进程导致 `winerror 10048`（端口占用）。**用 PowerShell 清理**：
```powershell
Get-NetTCPConnection -LocalPort 8000,8001,8002,8003,8004,8005,8006 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
```

---

## 4. 前端

```bash
cd src/frontend
npm install
npm run dev       # 开发服务器 http://localhost:3000，/api 代理到网关 :8000
npm run build     # 生产构建 -> dist/（tsc -b 类型检查 + vite build）
npm run preview   # 预览 dist/ 产物
```

构建说明：`vite.config.ts` 由 `tsconfig.node.json`（composite）处理，主 `tsconfig.json` 仅编译 `src`。
若遇 `TS6305 / TS6310`：删除 `*.tsbuildinfo` 与 `vite.config.js` / `vite.config.d.ts` 后重新 `npm run build`。
（这些文件已被 `.gitignore` 排除，属构建副产物。）

---

## 5. 向量库（Qdrant）切换

`knowledge-service` 支持三级，按优先级生效：

| 配置 | 形态 | 适用 |
|---|---|---|
| `QDRANT_URL=http://host:6333` | 独立 Qdrant 服务端 | 生产集群 |
| `QDRANT_LOCAL_PATH=./.qdrant_storage` | 嵌入式本地引擎（免服务端，落盘持久化） | 单机 / 边缘生产 |
| 两者皆空 | 进程内 InMemory | 默认 dev / 演示 |

本地引擎验证示例（无需 Docker）：
```bash
cd src/knowledge-service
QDRANT_LOCAL_PATH=./.qdrant_storage uvicorn app.main:app --port 8005
# 启动日志应出现：[vector_store] using Qdrant local engine @ ./.qdrant_storage
```

---

## 6. 数据库（PostgreSQL）切换

所有服务 `DATABASE_URL` 驱动（默认 `sqlite:///./<svc>.db`）。生产切换：
```bash
export DATABASE_URL=postgresql://wbadmin:wbsecret@postgres:5432/workbuddy
```
`src/deploy/docker-compose.yml` 已内置 PostgreSQL 服务并注入该变量。
本仓库 MVP 真实验证使用 sqlite 降级（无重型依赖亦可跑通），PG 端到端验证需起 PG 服务。

---

## 7. OIDC 单点登录

`auth-service` 配置（未配置 `OIDC_ISSUER` 时 `/auth/login` 返回 501 禁用）：
```bash
OIDC_ISSUER=https://keycloak.example.com/realms/workbuddy   # IdP issuer，自动读 .well-known/openid-configuration
OIDC_CLIENT_ID=workbuddy-web
OIDC_CLIENT_SECRET=*****
OIDC_REDIRECT_URI=http://localhost:8000/api/auth/callback   # 经网关回跳
OIDC_FRONTEND_REDIRECT=http://localhost:3000                 # 登录成功后前端落地页
OIDC_SCOPES=openid email profile
```
流程：前端点「企业账号登录」→ `GET /api/auth/login` → 302 到 IdP 授权端点 →
用户登录 → IdP 回跳 `OIDC_REDIRECT_URI?code=...&state=...` →
后端用 code 换 `id_token`、jwks(RS256) 验签 → 按 `sub`/`email` 查找或自动开通用户 →
mint 平台 JWT → 302 前端 `?access_token=...&refresh_token=...`（前端读取落地）。

支持任意标准 IdP：Keycloak / Azure AD / 飞书 / 企微 / Okta / Google Workspace。
`state` cookie（httpOnly）防 CSRF，`nonce` 防重放。

---

## 8. 真实验证要点（curl）

```bash
# 1) 本地登录拿 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/local \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2) RAG 闭环（knowledge-service :8005）
KB=$(curl -s -X POST http://localhost:8005/kb -H 'Content-Type: application/json' \
  -d '{"name":"demo","embedding":"bge-m3"}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -s -X POST http://localhost:8005/kb/$KB/ingest -F "file=@doc.txt;filename=doc.txt"
# 轮询 GET /kb/$KB/documents 直到 status=indexed，再：
curl -s -X POST http://localhost:8005/kb/$KB/search -H 'Content-Type: application/json' \
  -d '{"query":"self-hosted AI agent platform","top_k":3}'

# 3) 审计（必须经网关；直接打 audit :8006 返回 403 为安全设计）
curl -s http://localhost:8000/api/audit/events -H "Authorization: Bearer $TOKEN"

# 4) Agent 运行时（:8007，需先建好 KB / 技能 / MCP server 并代入对应 ID）
#    开启网关 agent 路由后，也可直接打网关 /api/v1/chat（自动转发到 :8007）
curl -s -X POST http://localhost:8007/agent/chat \
  -H 'Content-Type: application/json' \
  -d '{"model":"agent-mock","messages":[{"role":"user","content":"请帮我检索知识库中关于私有化部署的文档"}]}'
# 返回 {run_id, answer, steps, model}；steps 记录每次工具调用（search_kb / use_skill / call_mcp_tool）
```

> 启用 Agent 对话：gateway 设 `AGENT_CHAT_ENABLED=true` + `AGENT_SERVICE_URL=http://localhost:8007`，
> 之后 `POST /api/v1/chat` 会自动走 agent-runtime 编排（输入/输出均经内容审核）。

---

## 9. Agent 运行时与内容审核（阶段 2 新增）

### 9.1 Agent 运行时（agent-service :8007）

基于 LangGraph `StateGraph` 的 ReAct 循环，LLM 自主决定调用企业能力：`search_kb` / `use_skill` / `call_mcp_tool`。
两种 LLM 后端（同一套图，靠 `AGENT_ENABLE_MOCK_LLM` 切换）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `AGENT_ENABLE_MOCK_LLM` | `true` | `true`=确定性规则路由（无 GPU 环境验证全链路）；`false`=打 model-gateway 走真实工具调用 |
| `AGENT_MAX_STEPS` | `8` | 单轮对话最大工具调用步数（防无限循环） |
| `AGENT_DEFAULT_KB_ID` | 空 | mock 路由 `search_kb` 时使用的知识库 ID |
| `AGENT_DEFAULT_SKILL_ID` | 空 | mock 路由 `use_skill` 时使用的技能 ID |
| `AGENT_DEFAULT_MCP_SERVER_ID` | 空 | mock 路由 `call_mcp_tool` 时使用的 MCP server ID |
| `AGENT_DEFAULT_MCP_TOOL` | `echo` | 默认 MCP 工具名 |
| `AGENT_SERVICE_PORT` | `8007` | 服务端口 |

> 真实 LLM 模式（`AGENT_ENABLE_MOCK_LLM=false`）需要 model-gateway 后端接好 vLLM/SGLang（OpenAI 工具调用协议）。

### 9.2 内容审核管线（shared/moderation.py）

私有化部署合规护栏：防 PII / 涉密 / 暴力违法内容泄漏。纯正则 + 可配置词表，无外部依赖，可离线运行。
gateway（输入侧）与 agent-service（输入 + 输出侧）均已接入。

| 变量 | 默认 | 说明 |
|---|---|---|
| `MODERATION_ENABLED` | `true` | 总开关 |
| `MODERATION_MODE` | `redact` | `redact`（脱敏后放行）/ `block`（直接拒绝）/ `log`（仅记录） |
| `MODERATION_WORDLIST` | 空 | 敏感词表文件路径（每行一词，可扩充涉密/业务词），避免硬编码进代码库 |

- PII 检测：身份证 / 手机号 / 银行卡 / 邮箱（正则），`block` 模式直接拒，`redact` 模式打码。
- 敏感词：涉密级别词（绝密/机密/…）与暴力违法词（通用样例）；`block` 模式硬性拦截，`redact`/`log` 仅记录原因。
- 词表默认仅含通用样例，**不内置任何政治实体词**；企业应按等保/合规要求自行维护词表文件。

## 10. 常见问题

| 现象 | 原因 / 解决 |
|---|---|
| `winerror 10048` 端口占用 | Windows 用 PowerShell `Stop-Process` 清端口（见 §3），勿用 Git Bash `taskkill` |
| curl 上传文件 `(26) Failed to open/read` | Windows 下用 `cygpath -w` 转 Windows 路径，如 `@$(cygpath -w doc.txt)` |
| `TS6305 / TS6310` 前端构建失败 | 删 `*.tsbuildinfo` 与 `vite.config.js/.d.ts` 后重 `npm run build`（见 §4） |
| OIDC `/auth/login` 返回 501 | 未配置 `OIDC_ISSUER` / `OIDC_CLIENT_ID`，属正常禁用 |
| OIDC discovery 失败 | 后端需外网访问 IdP 的 `.well-known/openid-configuration` |
| 对话返回 `[mock] 未连接真实推理后端` | 无 vLLM/GPU；配置 `VLLM_API_BASE` 指向真实推理端点即走真实模型 |

---

_Generated by WorkBuddy lead · 2026-08-09_
