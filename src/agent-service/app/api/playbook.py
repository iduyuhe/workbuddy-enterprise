"""智能体剧本 REST 路由（标杆 POC 铺包目标资源）。

与 agent-runtime 共享 `/agent` 前缀（经网关为 `/api/agent`），新增：
  POST   /agent/playbooks         创建
  GET    /agent/playbooks         列表（按租户隔离）
  GET    /agent/playbooks/{id}    详情
  PATCH  /agent/playbooks/{id}    更新（含 defaults / scenario_flow）
  DELETE /agent/playbooks/{id}    删除
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.playbook import AgentPlaybook
from app.schemas.playbook import PlaybookCreate, PlaybookOut, PlaybookUpdate

router = APIRouter()

HEADER_TENANT = "X-Tenant-Id"
HEADER_PROJECT = "X-Project-Id"


def _tenant_from_header(request: Request) -> str | None:
    return request.headers.get(HEADER_TENANT) or request.headers.get(HEADER_PROJECT)


def _to_out(pb: AgentPlaybook) -> PlaybookOut:
    return PlaybookOut(
        id=str(pb.id),
        tenant_id=pb.tenant_id,
        project_id=pb.project_id,
        name=pb.name,
        model=pb.model,
        system_prompt=pb.system_prompt,
        defaults=pb.defaults or {},
        scenario_flow=pb.scenario_flow or [],
        is_public=bool(pb.is_public),
        created_at=pb.created_at.isoformat() if pb.created_at else None,
        updated_at=pb.updated_at.isoformat() if pb.updated_at else None,
    )


@router.post("/agent/playbooks", response_model=PlaybookOut, status_code=201)
def create_playbook(payload: PlaybookCreate, request: Request, db: Session = Depends(get_db)):
    tenant = payload.tenant_id or _tenant_from_header(request)
    pb = AgentPlaybook(
        name=payload.name,
        model=payload.model,
        system_prompt=payload.system_prompt,
        defaults=payload.defaults,
        scenario_flow=payload.scenario_flow,
        is_public=payload.is_public,
        tenant_id=tenant,
        project_id=payload.project_id or tenant,
    )
    db.add(pb)
    db.commit()
    db.refresh(pb)
    return _to_out(pb)


@router.get("/agent/playbooks")
def list_playbooks(
    tenant_id: str | None = Query(None),
    db: Session = Depends(get_db),
    request: Request = None,
):
    tid = tenant_id or _tenant_from_header(request) if request else None
    stmt = select(AgentPlaybook)
    if tid:
        stmt = stmt.where(AgentPlaybook.tenant_id == tid)
    rows = db.scalars(stmt.order_by(AgentPlaybook.created_at.desc())).all()
    return {"items": [_to_out(r).model_dump() for r in rows], "total": len(rows)}


@router.get("/agent/playbooks/{playbook_id}", response_model=PlaybookOut)
def get_playbook(playbook_id: uuid.UUID, db: Session = Depends(get_db)):
    pb = db.get(AgentPlaybook, str(playbook_id))
    if not pb:
        raise HTTPException(status_code=404, detail="playbook not found")
    return _to_out(pb)


@router.patch("/agent/playbooks/{playbook_id}", response_model=PlaybookOut)
def update_playbook(playbook_id: uuid.UUID, payload: PlaybookUpdate, db: Session = Depends(get_db)):
    pb = db.get(AgentPlaybook, str(playbook_id))
    if not pb:
        raise HTTPException(status_code=404, detail="playbook not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(pb, k, v)
    db.commit()
    db.refresh(pb)
    return _to_out(pb)


@router.delete("/agent/playbooks/{playbook_id}")
def delete_playbook(playbook_id: uuid.UUID, db: Session = Depends(get_db)):
    pb = db.get(AgentPlaybook, str(playbook_id))
    if not pb:
        raise HTTPException(status_code=404, detail="playbook not found")
    db.delete(pb)
    db.commit()
    return {"deleted": str(playbook_id)}
