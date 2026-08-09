"""mcp-connector 配置（env 驱动）。"""
import os

SERVICE_NAME = "mcp-connector"
PORT = int(os.getenv("PORT", "8004"))

HEADER_USER_ID = "X-User-Id"
HEADER_PROJECT_ID = "X-Project-Id"

# 调用 MCP server 的超时（秒）
MCP_CALL_TIMEOUT = float(os.getenv("MCP_CALL_TIMEOUT", "30"))
