"""Chat endpoint: KB aggregation + SSE passthrough to model-gateway/agent-runtime + async audit."""
from __future__ import annotations

from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from app.core.config import AGENT_CHAT_ENABLED, AGENT_SERVICE_URL, MODEL_GATEWAY_URL
from app.core.security import Principal, authenticate
from app.core.rbac import check_rbac
from app.services.audit_client import send_audit
from app.services.kb import gather_kb_context
from shared.moderation import moderate
from shared.schemas.common import AuditEvent
from shared.schemas.errors import error_response, new_req_id


def _last_user_content(messages: list) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            c = m.get("content", "")
            return c if isinstance(c, str) else ""
    return ""


async def chat_entry(request: Request) -> Response:
    principal = authenticate(request)

    # RBAC: chat:send + kb:read
    if not await check_rbac(request.app.state.http, "chat:send", principal.user_id, principal.project_id):
        return error_response(403, "RBAC_DENIED", "action chat:send not allowed", new_req_id())
    if not await check_rbac(request.app.state.http, "kb:read", principal.user_id, principal.project_id):
        return error_response(403, "RBAC_DENIED", "action kb:read not allowed", new_req_id())

    payload = await request.json()
    model = payload.get("model")
    messages = payload.get("messages", [])

    # 输入内容审核（防御入口；agent 路径下输出审核在 agent-service 完成）
    query = _last_user_content(messages)
    mod = moderate(query, "input")
    if mod.blocked:
        return error_response(403, "CONTENT_BLOCKED", f"输入被内容审核拦截：{mod.reasons}", new_req_id())
    if mod.text and mod.text != query:
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "user":
                m["content"] = mod.text
                break

    # agent 运行时开启时，对话走 agent-service（会自行做 RAG/技能/MCP 编排）
    if AGENT_CHAT_ENABLED:
        target = f"{AGENT_SERVICE_URL}/agent/chat"
        headers = {
            "Content-Type": "application/json",
            "X-User-Id": principal.user_id,
            "X-Project-Id": principal.project_id or "",
        }
        return await _stream_proxy(request, target, headers, principal, model)

    # aggregate KB context (degrades to "" if KB unavailable)
    context = await gather_kb_context(request.app.state.http, principal.project_id, query, principal.user_id)
    if context:
        payload["messages"] = [{"role": "system", "content": context}] + messages

    target = f"{MODEL_GATEWAY_URL}/v1/chat"
    headers = {
        "Content-Type": "application/json",
        "X-User-Id": principal.user_id,
        "X-Project-Id": principal.project_id or "",
    }
    return await _stream_proxy(request, target, headers, principal, model)


async def _stream_proxy(
    request: Request, target: str, headers: dict, principal: Principal, model: str | None
) -> Response:
    payload = await request.json() if request.method == "POST" else {}
    req_id = new_req_id()
    client = request.app.state.http
    ip = request.client.host if request.client else None

    async def event_stream():
        try:
            async with client.stream(
                "POST", target, json=payload, headers=headers, timeout=120
            ) as resp:
                async for chunk in resp.aiter_text():
                    yield chunk
        finally:
            await send_audit(
                client,
                AuditEvent(
                    actor_id=principal.user_id,
                    actor_name=principal.username,
                    project_id=principal.project_id,
                    action="chat",
                    resource="conv:" + req_id,
                    req_id=req_id,
                    model=model,
                    ip=ip,
                    detail={"stream": True, "target": target},
                ),
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
