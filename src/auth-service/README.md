# auth-service (:8002)

认证授权 + RBAC 服务。职责（见 ARCHITECTURE §2 / API_CONTRACT §1）：

- 本地登录 `POST /auth/login/local`（种子 admin/admin123）
- OIDC 起点/回调（留 TODO）
- 刷新 `POST /auth/token/refresh`
- 当前用户 `GET /auth/me`
- 内部 RBAC 校验 `POST /auth/rbac/check`
- 用户 / 角色 / 权限 / 项目 / 团队成员 CRUD

下游服务信任网关注入的 `X-User-Id` / `X-Project-Id` 头；本服务对这些头与 JWT 都认。

## 运行
```bash
cd src/auth-service
pip install -r requirements.txt
uvicorn app.main:app --port 8002 --reload
```

## 环境变量
- `DATABASE_URL`（默认 sqlite:///./auth.db）
- `JWT_SECRET`（默认 dev-secret-change-me，生产必改）
- `JWT_ALGORITHM`（默认 HS256）
- `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD`（默认 admin/admin123）
