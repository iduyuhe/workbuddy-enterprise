"""Chat / completions / models endpoints (OpenAI-compatible)."""
from __future__ import annotations

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.services.provider import router

api = APIRouter(tags=["model"])


@api.post("/v1/chat")
async def chat(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    payload = await request.json()
    model = payload.get("model")
    provider = router.resolve(model)
    stream = bool(payload.get("stream", False))
    if stream:
        return StreamingResponse(
            provider.chat_stream(payload),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    result = await provider.chat(payload)
    return JSONResponse(content=result)


@api.post("/v1/completions")
async def completions(request: Request):
    payload = await request.json()
    provider = router.resolve(payload.get("model"))
    result = await provider.chat(payload)
    return JSONResponse(content=result)


@api.get("/v1/models")
async def list_models():
    from app.core.config import MODEL_CATALOG

    models = []
    for mid, meta in MODEL_CATALOG.items():
        models.append(
            {
                "id": mid,
                "provider": meta["provider"],
                "context_window": meta["context_window"],
                "owned_by": "workbuddy",
            }
        )
    return {"models": models, "object": "list"}
