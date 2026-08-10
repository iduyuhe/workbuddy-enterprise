"""Audit persistence + query + CSV export."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import AUDIT_ENC_KEY
from app.models.audit import AuditLog
from shared.crypto import sm3_hex, sm4_decrypt, sm4_encrypt


def _canonical(log: AuditLog, detail_plain: str | None) -> str:
    """用于完整性杂凑的规范化字符串（不含 id/ts/integrity_hash）。"""
    fields = [
        log.actor_id or "",
        log.actor_name or "",
        log.project_id or "",
        log.action or "",
        log.resource or "",
        log.req_id or "",
        log.model or "",
        str(log.tokens_in or ""),
        str(log.tokens_out or ""),
        log.ip or "",
        detail_plain or "",
    ]
    return "|".join(fields)


def _encrypt_detail(plain: str | None) -> tuple[str | None, int]:
    """返回 (存储值, enc_ver)。plain=None 则不加密。"""
    if plain is None:
        return None, 0
    import base64

    blob = sm4_encrypt(AUDIT_ENC_KEY, plain.encode("utf-8"))
    return base64.b64encode(blob).decode("ascii"), 1


def _decrypt_detail(stored: str | None, enc_ver: int | None) -> str | None:
    if stored is None:
        return None
    if enc_ver != 1:
        return stored
    import base64

    blob = base64.b64decode(stored)
    return sm4_decrypt(AUDIT_ENC_KEY, blob).decode("utf-8")


def _to_row(log: AuditLog) -> dict:
    detail_plain = _decrypt_detail(log.detail_json, log.enc_ver)
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
        "detail": detail_plain,
        "integrity_hash": log.integrity_hash,
    }


def create_event(db: Session, event: dict) -> int:
    detail = event.get("detail")
    detail_plain = json.dumps(detail, ensure_ascii=False) if detail is not None else None
    detail_stored, enc_ver = _encrypt_detail(detail_plain)
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
        detail_json=detail_stored,
        enc_ver=enc_ver,
    )
    # 等保三级 · 数据完整性：落库前对关键字段做 SM3 杂凑
    log.integrity_hash = sm3_hex(_canonical(log, detail_plain).encode("utf-8"))
    db.add(log)
    db.commit()
    db.refresh(log)
    return log.id


def verify_event_integrity(db: Session, log_id: int) -> bool:
    """重新计算并比对完整性哈希（防篡改检测）。"""
    log = db.get(AuditLog, log_id)
    if not log:
        return False
    detail_plain = _decrypt_detail(log.detail_json, log.enc_ver)
    return log.integrity_hash == sm3_hex(_canonical(log, detail_plain).encode("utf-8"))


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
