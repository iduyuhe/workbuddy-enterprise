"""Audit API: events write / query / export."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services import audit_service

api = APIRouter(tags=["audit"])


class AuditEventReq(BaseModel):
    actor_id: str | None = None
    actor_name: str | None = None
    project_id: str | None = None
    action: str
    resource: str | None = None
    req_id: str | None = None
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    ip: str | None = None
    detail: dict | None = None


@api.post("/audit/events")
async def write_event(body: AuditEventReq, db: Session = Depends(get_db)):
    # accept internal caller only (gateway injects X-User-Id); allow unauthenticated
    # writes from the internal network per MVP trust model.
    event_id = audit_service.create_event(db, body.model_dump())
    return {"id": event_id}


@api.get("/audit/events")
async def list_events(
    project_id: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    frm: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    # MVP: require internal caller header for reads. TODO: enforce auditor/admin RBAC.
    if not x_user_id:
        raise HTTPException(status_code=403, detail="internal only")
    return audit_service.query_events(
        db, project_id=project_id, actor_id=actor_id, action=action,
        frm=frm, to=to, page=page, size=size,
    )


@api.get("/audit/export")
async def export_events(
    project_id: str | None = Query(default=None),
    frm: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    if not x_user_id:
        raise HTTPException(status_code=403, detail="internal only")
    csv_text = audit_service.export_csv(db, project_id=project_id, frm=frm, to=to)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_export.csv"},
    )
