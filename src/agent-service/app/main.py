"""agent-runtime entrypoint (FastAPI :8007)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from fastapi import FastAPI

from app.api import agent
from app.core.db import init_db

app = FastAPI(title="WorkBuddy Enterprise agent-runtime", version="1.0.0")
app.include_router(agent.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-runtime"}
