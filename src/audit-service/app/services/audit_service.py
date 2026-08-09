"""Audit persistence + query + CSV export."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def _to_row(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "ts": log.ts,
        "actor_id": log.actor_id,
        "actor_name": log.actor_name,
        "project_id": log.project_id,
        "action": log.action,
        "resource": log.resource,
        "req_id": log.req_id,
        "model": log.model,
        "tokens_in": log.tokens_in,
        "tokens_out": log.tokens_out,
        "ip": log.ip,
        "detail": log.detail_json,
    }


def create_event(db: Session, event: dict) -> int:
    detail = event.get("detail")
    log = AuditLog(
        actor_id=event.get("actor_id"),
        actor_name=event.get("actor_name"),
        project_id=event.get("project_id"),
        action=event.get("action"),
        resource=event.get("resource"),
        req_id=event.get("req_id"),
        model=event.get("model"),
        tokens_in=event.get("tokens_in"),
        tokens_out=event.get("tokens_out"),
        ip=event.get("ip"),
        detail_json=json.dumps(detail, ensure_ascii=False) if detail is not None else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log.id


def query_events(
    db: Session,
    *,
    project_id: str | None = None,
    actor_id: str | None = None,
    action: str | None = None,
    frm: str | None = None,
    to: str | None = None,
    page: int = 1,
    size: int = 20,
):
    stmt = select(AuditLog)
    if project_id:
        stmt = stmt.where(AuditLog.project_id == project_id)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if frm:
        stmt = stmt.where(AuditLog.ts >= frm)
    if to:
        stmt = stmt.where(AuditLog.ts <= to)
    total = len(db.execute(stmt.with_only_columns(AuditLog.id)).all())
    stmt = stmt.order_by(AuditLog.id.desc()).limit(size).offset((page - 1) * size)
    rows = db.execute(stmt).scalars().all()
    return {"items": [_to_row(r) for r in rows], "total": total, "page": page, "size": size}


def export_csv(db: Session, *, project_id: str | None = None, frm: str | None = None, to: str | None = None) -> str:
    stmt = select(AuditLog)
    if project_id:
        stmt = stmt.where(AuditLog.project_id == project_id)
    if frm:
        stmt = stmt.where(AuditLog.ts >= frm)
    if to:
        stmt = stmt.where(AuditLog.ts <= to)
    rows = db.execute(stmt.order_by(AuditLog.id.asc())).scalars().all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "ts", "actor_id", "actor_name", "project_id", "action",
         "resource", "req_id", "model", "tokens_in", "tokens_out", "ip", "detail"]
    )
    for r in rows:
        row = _to_row(r)
        writer.writerow(
            [row["id"], row["ts"], row["actor_id"], row["actor_name"], row["project_id"],
             row["action"], row["resource"], row["req_id"], row["model"],
             row["tokens_in"], row["tokens_out"], row["ip"], row["detail"]]
        )
    return buf.getvalue()
