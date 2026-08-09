"""Shared outbound httpx client + small helpers for the gateway."""
from __future__ import annotations

import asyncio

import httpx


def make_client() -> httpx.AsyncClient:
    # trust_env=False: do NOT route localhost through any system HTTP(S) proxy.
    return httpx.AsyncClient(
        timeout=httpx.Timeout(120.0),
        limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        trust_env=False,
    )


def client_ip(request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


async def call_fire_and_forget(coro):
    """Run a coroutine without blocking the response (best-effort)."""
    try:
        await coro
    except Exception:
        pass
