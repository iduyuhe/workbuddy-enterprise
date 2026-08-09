"""MCP 协议客户端（简化中继实现）。

MVP 阶段：聚焦「注册 + 存储 + 中继框架」。
- sse / http transport：通过 JSON-RPC 2.0 向 endpoint 发送 tools/list、tools/call。
- stdio transport：# TODO 阶段 2 通过子进程拉起 MCP server 并双向通信。

说明：真实 MCP 的 SSE transport 需要「POST 到 messages 端点 + 监听 SSE 流」的握手，
此处对纯 JSON 响应与 text/event-stream 响应均做了最小兼容解析，足以对接
streamable-http / 简单 HTTP 形态的 MCP server。完整 SSE 会话管理以下方 TODO 标注。
"""
import json
import uuid

import httpx

from app.core.config import MCP_CALL_TIMEOUT


async def _jsonrpc_post(endpoint: str, method: str, params: dict, timeout: float) -> dict:
    """向 MCP endpoint 发送一次 JSON-RPC 请求，返回 result 字段。

    兼容两种响应：
      - application/json：直接解析为 JSON-RPC 响应
      - text/event-stream：逐行解析 `data:` 帧，取第一个含 result/error 的帧
    """
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),

        "method": method,
        "params": params,
    }
    # TODO(阶段2): 完整 SSE transport 应：
    #   1) 先 GET endpoint 建立 SSE 流拿到 session_id
    #   2) 将请求 POST 到 <endpoint>?session_id=... 的 messages 端点
    #   3) 从 SSE 流中按 id 匹配本次响应
    # 当前实现直接 POST 到 endpoint，适配 streamable-http / 简化 HTTP MCP server。
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            endpoint,
            json=payload,
            headers={"Accept": "application/json, text/event-stream"},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            result = None
            for line in resp.text.splitlines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                try:
                    frame = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if frame.get("id") == payload["id"]:
                    result = frame
                    break
            if result is None:
                raise RuntimeError("no matching SSE frame for jsonrpc id")
        else:
            result = resp.json()

    if "error" in result and result["error"] is not None:
        raise RuntimeError(f"mcp error: {result['error']}")
    return result.get("result", {})


async def list_tools(endpoint: str, timeout: float = MCP_CALL_TIMEOUT) -> list[dict]:
    """调用 MCP tools/list，返回工具清单列表（每个含 name / description / inputSchema）。"""
    res = await _jsonrpc_post(endpoint, "tools/list", {}, timeout)
    return res.get("tools", [])


async def call_tool(
    endpoint: str, tool_name: str, arguments: dict, timeout: float = MCP_CALL_TIMEOUT
) -> dict:
    """调用 MCP tools/call，返回 result 内容。"""
    res = await _jsonrpc_post(
        endpoint, "tools/call",
        {"name": tool_name, "arguments": arguments},
        timeout,
    )
    return res
