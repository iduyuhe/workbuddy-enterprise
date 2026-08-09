# mcp-connector — MCP 连接器

## 职责
- 复用 WorkBuddy 现有 MCP 生态：注册/发现 MCP Server。
- 同步工具清单（schema），中继工具调用。
- 凭据托管（引用密钥管理，不落明文）。

## 技术栈
Python 3.11 + FastAPI + httpx（stdio/sse 客户端）+ Pydantic。
（阶段 2 引入官方 `mcp` Python SDK 做 stdio 进程管理。）

## 运行方式
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8004
```
环境变量：`DATABASE_URL`、`SECRET_BACKEND`。

## 实现团队
后端 + AI（工具调用协议对接 agent-runtime）。
