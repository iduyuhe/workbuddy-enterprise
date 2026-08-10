# agent-service（Agent 运行时，端口 8007）

WorkBuddy Enterprise 的 **Agent 编排运行时**：用 LangGraph `StateGraph` 实现 ReAct 循环，
让 LLM 自主决定调用哪些企业能力：

- `search_kb` —— 经 knowledge-service 真实执行 RAG 检索
- `use_skill` —— 取已注册企业技能（Anthropic Skills 规范）的执行指引
- `call_mcp_tool` —— 经 mcp-connector 真实 relay 到 MCP server（sse/http）

## 两种 LLM 后端（同一套图）

| 模式 | 开关 | 行为 |
| --- | --- | --- |
| 真实 | `AGENT_ENABLE_MOCK_LLM=false` | `call_llm` 打 model-gateway `/v1/chat`（透传 vLLM/SGLang 的 OpenAI 工具调用） |
| Mock（默认） | `AGENT_ENABLE_MOCK_LLM=true` | 确定性规则路由，用于无 GPU 环境验证「图编排 + 工具真实执行」全链路 |

## 启动

```bash
pip install -r requirements.txt
AGENT_ENABLE_MOCK_LLM=true \
AGENT_DEFAULT_KB_ID=<kb_id> \
AGENT_DEFAULT_SKILL_ID=<skill_id> \
AGENT_DEFAULT_MCP_SERVER_ID=<server_id> AGENT_DEFAULT_MCP_TOOL=<tool> \
python -m uvicorn app.main:app --port 8007
```

## 接口

- `POST /agent/chat` —— `{model, messages, stream?}`，返回 `{run_id, answer, steps, model}`（stream=true 时吐 OpenAI 兼容 SSE）
- `GET  /agent/tools` —— 当前 agent 可用工具清单
- `GET  /agent/runs` —— 历史运行记录（可观测性 / 审计）

## 部署

由 `src/deploy/docker-compose.yml` 编排；gateway 在 `AGENT_CHAT_ENABLED=true` 时把
`/api/v1/chat` 路由到本服务，实现「对话即经过 agent 运行时」。
