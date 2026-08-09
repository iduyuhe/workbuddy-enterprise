"""KB context aggregation: list KBs for a project, search the first, build a system prompt."""
from __future__ import annotations

import httpx

from app.core.config import KB_SERVICE_URL


async def gather_kb_context(
    client: httpx.AsyncClient,
    project_id: str | None,
    query: str,
    x_user_id: str,
) -> str:
    """Return aggregated context string, or "" if unavailable/failed."""
    if not query:
        return ""
    headers = {
        "X-User-Id": x_user_id,
        "X-Project-Id": project_id or "",
    }
    try:
        # 1) list knowledge bases for this project
        r = await client.get(
            f"{KB_SERVICE_URL}/kb",
            params={"project_id": project_id},
            headers=headers,
            timeout=10,
        )
        data = r.json()
        kbs = (data.get("items") or []) if isinstance(data, dict) else []
        if not kbs:
            return ""
        kb_id = kbs[0]["id"]

        # 2) search
        r2 = await client.post(
            f"{KB_SERVICE_URL}/kb/{kb_id}/search",
            json={"query": query, "top_k": 5, "rerank": True, "score_threshold": 0.3},
            headers=headers,
            timeout=10,
        )
        res = r2.json()
        chunks = (res.get("results") or []) if isinstance(res, dict) else []
        if not chunks:
            return ""
        parts = [c.get("content", "") for c in chunks if c.get("content")]
        if not parts:
            return ""
        return "以下是企业知识库中的相关上下文，请在回答时优先参考：\n\n" + "\n\n".join(parts)
    except httpx.HTTPError:
        # knowledge-service unreachable -> degrade gracefully (no context)
        return ""
