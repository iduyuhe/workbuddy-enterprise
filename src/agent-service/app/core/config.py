"""agent-runtime 配置：下游服务地址 + 运行参数。"""
from __future__ import annotations

import os


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _bool(key: str, default: bool) -> bool:
    return os.getenv(key, "true" if default else "false").lower() in ("1", "true", "yes", "on")


AGENT_SERVICE_PORT = int(_env("AGENT_SERVICE_PORT", "8007"))

MODEL_GATEWAY_URL = _env("MODEL_GATEWAY_URL", "http://localhost:8001")
SKILLS_SERVICE_URL = _env("SKILLS_SERVICE_URL", "http://localhost:8003")
MCP_SERVICE_URL = _env("MCP_SERVICE_URL", "http://localhost:8004")
KB_SERVICE_URL = _env("KB_SERVICE_URL", "http://localhost:8005")

# 编排参数
AGENT_MAX_STEPS = int(_env("AGENT_MAX_STEPS", "8"))
# 默认开启 mock LLM：本仓库 MVP 常在无 GPU/vLLM 的环境运行，
# 设为 true 时走确定性规则路由（可验证 ReAct 全链路）；
# 接好 vLLM/SGLang 后设 false，走真实 LangGraph + 工具调用。
ENABLE_MOCK_LLM = _bool("AGENT_ENABLE_MOCK_LLM", True)

# mock 路由所需的资源 ID（真实执行会打到这些资源）
AGENT_DEFAULT_KB_ID = _env("AGENT_DEFAULT_KB_ID", "")
AGENT_DEFAULT_SKILL_ID = _env("AGENT_DEFAULT_SKILL_ID", "")
AGENT_DEFAULT_MCP_SERVER_ID = _env("AGENT_DEFAULT_MCP_SERVER_ID", "")
AGENT_DEFAULT_MCP_TOOL = _env("AGENT_DEFAULT_MCP_TOOL", "echo")
