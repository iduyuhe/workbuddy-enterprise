# gateway (:8000)

唯一对外入口（BFF）。职责（API_CONTRACT §7 / ARCHITECTURE §5）：

1. 校验 JWT（PyJWT HS256，密钥读 JWT_SECRET）。
2. 每次受保护请求做 RBAC 校验（调用 auth-service `/auth/rbac/check`）。
3. 注入内部信任头 `X-User-Id` / `X-Project-Id` 后转发到下游。
4. `POST /api/v1/chat`：先按 project 调 knowledge-service 检索聚合 KB 上下文，
   再以 SSE 透传 model-gateway；流结束后异步写审计事件到 audit-service。
5. 其余 `/api/*` 路由按前缀转发（auth / kb / skills / mcp / audit）。

下游服务地址通过 env 配置（默认 localhost 各端口）。

## 运行
```bash
cd src/gateway
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

## 环境变量
- `JWT_SECRET` / `JWT_ALGORITHM`（与 auth-service 一致）
- `AUTH_SERVICE_URL` / `MODEL_GATEWAY_URL` / `KB_SERVICE_URL`
- `SKILLS_SERVICE_URL` / `MCP_SERVICE_URL` / `AUDIT_SERVICE_URL`
