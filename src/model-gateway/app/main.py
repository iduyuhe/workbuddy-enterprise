"""model-gateway entrypoint (FastAPI :8001)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, chat
from app.core.db import init_db
from app.services.provider import build_default_providers, router
from shared.schemas.errors import error_response

app = FastAPI(title="WorkBuddy Enterprise model-gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.api)
app.include_router(admin.api)


def seed_providers():
    from app.core.db import SessionLocal
    from app.models.models import ModelProvider

    db = SessionLocal()
    try:
        for name, kind, base in [
            ("vllm", "vllm", os.getenv("VLLM_API_BASE", "http://localhost:8080/v1")),
            ("sglang", "sglang", os.getenv("DEEPSEEK_API_BASE", "http://localhost:8081/v1")),
            ("claude", "api", os.getenv("CLAUDE_API_BASE", "") or None),
        ]:
            existing = db.execute(
                __import__("sqlalchemy").select(ModelProvider).where(ModelProvider.name == name)
            ).scalar_one_or_none()
            if not existing:
                db.add(
                    ModelProvider(
                        name=name,
                        kind=kind,
                        base_url=base,
                        default_model={"vllm": "qwen3-235b", "sglang": "deepseek-v3", "claude": "claude"}.get(name),
                        enabled=True,
                    )
                )
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    init_db()
    build_default_providers()
    seed_providers()


@app.get("/health")
def health():
    return {"status": "ok", "service": "model-gateway", "providers": list(router.providers.keys())}
