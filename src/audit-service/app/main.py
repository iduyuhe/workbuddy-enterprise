"""audit-service entrypoint (FastAPI :8006)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit
from app.core.db import init_db

app = FastAPI(title="WorkBuddy Enterprise audit-service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit.api)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "audit-service"}
