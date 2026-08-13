# 快速开始

两种上手方式：本地轻量体验（无需 GPU），或生产级私有化部署（Docker Compose）。

## 方式一：本地轻量体验（无需 GPU）

适合开发者在笔记本上跑通最小闭环（使用 SQLite + 内存向量降级，不依赖 GPU / Qdrant / PostgreSQL）：

```bash
# 1. 后端依赖（建议虚拟环境）
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

## 方式二：生产级私有化部署（Docker Compose）

见 [`src/deploy/README.md`](https://github.com/iduyuhe/workbuddy-enterprise/blob/main/src/deploy/README.md)：

```bash
cp src/deploy/.env.example src/deploy/.env
# 将模型权重放到 /models（如 Qwen3-235B-A22B-FP8）
cd src/deploy && docker compose up -d
```

## 下一步

- 想接入企业知识？看 [系统架构](ARCHITECTURE.md) 的 knowledge-service 章节。
- 想写第一个技能？抄 [hello-skill 示例](examples/hello-skill.md)。
- 想上架到生态市场？看 [marketplace 最小包示例](examples/marketplace-package.md)。
- 想编排一个智能体？看 [agent 剧本示例](examples/agent-playbook.md)。
