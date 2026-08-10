"""agent-runtime REST 路由。"""
from __future__ import annotations

import json
import uuid

import httpx
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.db import SessionLocal
from app.core.config import AGENT_DEFAULT_MODEL
from app.models.run import AgentRun
from app.services.agent_runtime import run_agent
from app.services.catalog import build_agent_tools
from shared.schemas.errors import error_response, new_req_id

router = APIRouter()


def _last_user_text(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            c = m.get("content", "")
            return c if isinstance(c, str) else ""
    return ""


@router.post("/agent/chat")
async def agent_chat(request: Request):
    payload = await request.json()
    messages = payload.get("messages", [])
    model = payload.get("model", AGENT_DEFAULT_MODEL)
    stream = bool(payload.get("stream", False))
    user_id = request.headers.get("X-User-Id", "anon")
    project_id = request.headers.get("X-Project-Id", "")

    # 输入审核
    last = _last_user_text(messages)
    from shared.moderation import moderate

    mod = moderate(last, "input")
    if mod.blocked:
        return error_response(403, "CONTENT_BLOCKED", f"输入被内容审核拦截：{mod.reasons}", new_req_id())
    if mod.text and mod.text != last:
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "user":
                m["content"] = mod.text
                break

    run_id = str(uuid.uuid4())
    async with httpx.AsyncClient(trust_env=False) as http:
        answer, steps = await run_agent(messages, model, user_id, project_id, http)

    # 输出审核
    omod = moderate(answer, "output")
    if omod.blocked:
        return error_response(403, "CONTENT_BLOCKED", "输出被内容审核拦截", new_req_id())
    answer = omod.text

    # 持久化运行记录
    db = SessionLocal()
    try:
        rec = AgentRun(
            id=run_id,
            project_id=project_id or None,
            user_id=user_id,
            prompt=last,
            answer=answer,
            steps_json=steps,
            model=model,
            status="done",
        )
        db.add(rec)
        db.commit()
    finally:
        db.close()

    if stream:
        rid = "chatcmpl-" + run_id[:12]

        def gen():
            for s in steps:
                yield f": step {json.dumps(s, ensure_ascii=False)}\n\n"
            for chunk in answer.split():
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "id": rid,
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [{"index": 0, "delta": {"content": chunk + " "}}],
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
            yield (
                "data: "
                + json.dumps({"id": rid, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
                + "\n\n"
            )
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return JSONResponse({"run_id": run_id, "answer": answer, "steps": steps, "model": model})


@router.get("/agent/tools")
def list_tools():
    return {"tools": build_agent_tools()}


@router.get("/agent/runs")
def list_runs(limit: int = 20, tenant_id: str | None = Query(None)):
    db = SessionLocal()
    try:
        q = db.query(AgentRun)
        # 多租户：按租户隔离
        if tenant_id:
            q = q.where(AgentRun.tenant_id == tenant_id)
        rows = (
            q.order_by(AgentRun.created_at.desc())
            .limit(min(limit, 100))
            .all()
        )
        return {
            "items": [
                {
                    "id": r.id,
                    "project_id": r.project_id,
                    "user_id": r.user_id,
                    "prompt": r.prompt,
                    "answer": r.answer,
                    "model": r.model,
                    "status": r.status,
                    "steps": r.steps_json,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
            "total": len(rows),
        }
    finally:
        db.close()
