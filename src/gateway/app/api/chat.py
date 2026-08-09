"""Chat endpoint: KB aggregation + SSE passthrough to model-gateway + async audit."""
from __future__ import annotations

from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from app.core.config import MODEL_GATEWAY_URL
from app.core.security import Principal, authenticate
from app.core.rbac import check_rbac
from app.services.audit_client import send_audit
from app.services.kb import gather_kb_context
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

    # aggregate KB context (degrades to "" if KB unavailable)
    query = _last_user_content(messages)
    context = await gather_kb_context(request.app.state.http, principal.project_id, query, principal.user_id)
    if context:
        payload["messages"] = [{"role": "system", "content": context}] + messages

    target = f"{MODEL_GATEWAY_URL}/v1/chat"
    headers = {
        "Content-Type": "application/json",
        "X-User-Id": principal.user_id,
        "X-Project-Id": principal.project_id or "",
    }
    req_id = new_req_id()
    client = request.app.state.http
    ip = request.client.host if request.client else None

    async def event_stream():
        usage_in = usage_out = None
        try:
            async with client.stream("POST", target, json=payload, headers=headers, timeout=120) as resp:
                async for chunk in resp.aiter_text():
                    yield chunk
        finally:
            # best-effort audit after the stream completes
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
                    tokens_in=usage_in,
                    tokens_out=usage_out,
                    ip=ip,
                    detail={"stream": True},
                ),
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
