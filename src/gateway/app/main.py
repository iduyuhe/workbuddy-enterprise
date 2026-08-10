"""gateway entrypoint (FastAPI :8000) — single external entrypoint."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import proxy
from app.core.client import make_client
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware

app = FastAPI(title="WorkBuddy Enterprise gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 等保三级：传输安全响应头（先于 CORS 注入，确保覆盖所有响应）
app.add_middleware(SecurityHeadersMiddleware)
# 等保三级：按 IP 固定窗口限流（防爆破 / 防 DoS）
app.add_middleware(RateLimitMiddleware)

app.include_router(proxy.router)


@app.on_event("startup")
async def on_startup():
    app.state.http = make_client()


@app.on_event("shutdown")
async def on_shutdown():
    await app.state.http.aclose()


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}
