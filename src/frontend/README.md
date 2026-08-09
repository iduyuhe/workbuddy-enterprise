# frontend — 管理控制台（React / TypeScript）

## 职责
- 登录（OIDC 回调本地登录）+ 仪表盘。
- 知识库管理（上传/检索测试）、技能市场、MCP 连接器、审计视图、RBAC 管理。
- 消费 `docs/API_CONTRACT.md` 的 `/api/*` 入口。

## 技术栈
React 18 + TypeScript + Vite + Tailwind CSS + React Router + axios。
（生产由 nginx 托管静态产物，经反向代理到 gateway。）

## 运行方式
```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # 产出 dist/ 供 nginx
```
环境变量（.env）：`VITE_API_BASE=http://localhost:8000/api`、`VITE_OIDC_REDIRECT=...`

## 实现团队
前端。
