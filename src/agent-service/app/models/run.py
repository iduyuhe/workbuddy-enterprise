"""Agent 运行记录 ORM（可观测性 / 审计溯源）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.db import DATABASE_URL, Base

# SQLite 用原生 JSON 类型（落为 TEXT/亲和类型）；PostgreSQL 用通用 JSON（落为 JSONB）。
try:
    if DATABASE_URL.startswith("sqlite"):
        from sqlalchemy.dialects.sqlite import JSON as _JSON
    else:
        from sqlalchemy.types import JSON as _JSON
except Exception:  # pragma: no cover
    from sqlalchemy.types import JSON as _JSON


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    thread_id = Column(String(36), nullable=True, index=True)
    prompt = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    steps_json = Column(_JSON, nullable=True)  # list[dict] 工具调用轨迹
    model = Column(String(64), nullable=True)
    status = Column(String(16), default="done")
    created_at = Column(DateTime, default=datetime.utcnow)
