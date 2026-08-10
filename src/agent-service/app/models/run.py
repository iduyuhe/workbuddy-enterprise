"""Agent 运行记录 ORM（可观测性 / 审计溯源）。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.types import JSON as GenericJSON

from app.core.db import Base

try:  # sqlite 用原生 JSON 类型；PG 用通用 JSON
    _JSON = SQLiteJSON
except Exception:  # pragma: no cover
    _JSON = GenericJSON


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
