"""Audit log ORM (ARCHITECTURE §4: audit_logs)."""
from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Column, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_ts", "ts"),
        Index("ix_audit_actor", "actor_id"),
        Index("ix_audit_project", "project_id"),
        Index("ix_audit_req", "req_id"),
    )

    # NOTE: SQLite only auto-increments INTEGER PRIMARY KEY; BIGINT PK would fail
    # with "NOT NULL constraint failed: audit_logs.id". Integer works on both
    # SQLite (rowid alias, autoincrement) and Postgres.
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(Text, default=lambda: __import__("datetime").datetime.utcnow().isoformat())
    actor_id = Column(String(36), nullable=True)
    actor_name = Column(String(128), nullable=True)
    project_id = Column(String(36), nullable=True)
    action = Column(String(64), nullable=True)
    resource = Column(String(128), nullable=True)
    req_id = Column(String(36), nullable=True)
    model = Column(String(64), nullable=True)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    ip = Column(String(64), nullable=True)
    detail_json = Column(Text, nullable=True)  # JSON string
