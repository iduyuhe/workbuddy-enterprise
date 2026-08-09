"""RBAC check client: calls auth-service /auth/rbac/check (fail-closed)."""
from __future__ import annotations

import httpx

from app.core.config import AUTH_SERVICE_URL


async def check_rbac(
    client: httpx.AsyncClient,
    action: str,
    user_id: str,
    project_id: str | None,
) -> bool:
    """Return True if allowed. Fail closed on any error (deny)."""
    try:
        resp = await client.post(
            f"{AUTH_SERVICE_URL}/auth/rbac/check",
            json={"user_id": user_id, "project_id": project_id, "action": action},
            timeout=10,
        )
        if resp.status_code == 200:
            return bool(resp.json().get("allowed", False))
        return False
    except httpx.HTTPError:
        # Fail closed: if auth-service is unreachable we must not grant access.
        return False
