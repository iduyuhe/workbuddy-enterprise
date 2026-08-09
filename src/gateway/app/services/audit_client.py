"""Fire-and-forget audit event sender."""
from __future__ import annotations

import httpx

from app.core.config import AUDIT_SERVICE_URL
from shared.schemas.common import AuditEvent


async def send_audit(client: httpx.AsyncClient, event: AuditEvent) -> None:
    try:
        await client.post(
            f"{AUDIT_SERVICE_URL}/audit/events",
            json=event.model_dump(),
            timeout=10,
        )
    except httpx.HTTPError:
        # audit must not block the main request path
        pass
