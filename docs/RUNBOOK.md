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

各服务独立启动（以 knowledge-service 为例）：
```bash
cd src/knowledge-service
uvicorn app.main:app --port 8005
```
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
```

---

## 9. 常见问题

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
