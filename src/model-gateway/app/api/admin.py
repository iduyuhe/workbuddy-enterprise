"""Admin: model routing config + API key (BYOK) management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import ModelKey, ModelProvider
from app.services.provider import router

api = APIRouter(tags=["admin"])


# ---------- routing ----------
class RouteConfig(BaseModel):
    project_id: str | None = None
    prefer: list[str] = []
    fallback: str | None = None


@api.get("/admin/routes")
async def get_routes():
    return {"routes": router.route_table}


@api.put("/admin/routes")
async def set_routes(body: RouteConfig):
    key = body.project_id or "*"
    router.route_table[key] = body.model_dump()
    return {"project_id": body.project_id, "config": body.model_dump()}


# ---------- keys (BYOK) ----------
class CreateKeyReq(BaseModel):
    provider: str
    scope: str = "tenant"  # tenant | user
    owner_id: str | None = None
    secret_ref: str  # reference to secret manager, NEVER plaintext
    label: str | None = None


@api.post("/admin/keys")
async def create_key(body: CreateKeyReq, db: Session = Depends(get_db)):
    provider = db.execute(
        select(ModelProvider).where(ModelProvider.name == body.provider)
    ).scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=400, detail=f"unknown provider: {body.provider}")
    key = ModelKey(
        provider_id=provider.id,
        label=body.label,
        api_key_ref=body.secret_ref,  # stored as reference only
        scope=body.scope,
        owner_id=body.owner_id,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    # never echo the secret ref back in full in MVP (could mask in future)
    return {"id": key.id, "provider": body.provider, "scope": body.scope, "label": body.label}


@api.get("/admin/keys")
async def list_keys(owner_id: str | None = None, db: Session = Depends(get_db)):
    stmt = select(ModelKey)
    if owner_id:
        stmt = stmt.where(ModelKey.owner_id == owner_id)
    rows = db.execute(stmt).scalars().all()
    items = [
        {
            "id": k.id,
            "provider_id": k.provider_id,
            "label": k.label,
            "scope": k.scope,
            "owner_id": k.owner_id,
            # api_key_ref intentionally omitted from list for safety
        }
        for k in rows
    ]
    return {"items": items, "total": len(items), "page": 1, "size": len(items)}
