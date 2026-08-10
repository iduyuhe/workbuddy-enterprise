"""工具适配器：把 agent 的工具调用真实转发到对应微服务。

- use_skill：取技能 manifest 作为执行指引（Anthropic Skills 文件式规范，指令即执行）
- call_mcp_tool：经 mcp-connector 真实 relay 到 MCP server（sse/http）
- search_kb：经 knowledge-service 真实执行 RAG 检索
"""
from __future__ import annotations

import httpx

from app.core.config import KB_SERVICE_URL, MCP_SERVICE_URL, SKILLS_SERVICE_URL


async def use_skill(
    client: httpx.AsyncClient,
    skill_id: str,
    args: dict | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
) -> dict:
    headers = {"X-User-Id": user_id or "", "X-Project-Id": project_id or ""}
    r = await client.get(f"{SKILLS_SERVICE_URL}/skills/{skill_id}", headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    manifest = data.get("manifest") or {}
    return {
        "skill_id": str(skill_id),
        "name": data.get("name"),
        "description": data.get("description"),
        "instructions": manifest.get("body_preview") or "",
        "args": args or {},
    }


async def call_mcp_tool(
    client: httpx.AsyncClient,
    server_id: str,
    tool_name: str,
    arguments: dict | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
) -> dict:
    headers = {"X-User-Id": user_id or "", "X-Project-Id": project_id or ""}
    r = await client.post(
        f"{MCP_SERVICE_URL}/mcp/servers/{server_id}/tools/{tool_name}/call",
        json={"arguments": arguments or {}},
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


async def search_kb(
    client: httpx.AsyncClient,
    kb_id: str,
    query: str,
    top_k: int = 3,
    user_id: str | None = None,
    project_id: str | None = None,
) -> dict:
    headers = {"X-User-Id": user_id or "", "X-Project-Id": project_id or ""}
    r = await client.post(
        f"{KB_SERVICE_URL}/kb/{kb_id}/search",
        json={"query": query, "top_k": top_k},
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()
