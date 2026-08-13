"""智能体剧本 ORM（标杆 POC 铺包目标资源之一）。

剧本描述一个「Killer Scenario」所需的默认接线（默认知识库 / 技能 / MCP 连接器）
与步骤编排（scenario_flow），供 agent-runtime 的 ReAct 循环消费。多租户隔离键 tenant_id。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text

from app.core.db import DATABASE_URL, Base

# SQLite 用原生 JSON 类型（落为 TEXT/亲和类型）；PostgreSQL 用通用 JSON（落为 JSONB）。
try:
    if DATABASE_URL.startswith("sqlite"):
        from sqlalchemy.dialects.sqlite import JSON as _JSON
    else:
        from sqlalchemy.types import JSON as _JSON
except Exception:  # pragma: no cover
    from sqlalchemy.types import JSON as _JSON


class AgentPlaybook(Base):
    __tablename__ = "agent_playbooks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=True, index=True)
    project_id = Column(String(36), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    model = Column(String(64), nullable=True)
    system_prompt = Column(Text, nullable=True)
    # 默认接线：{kb_id, skill_id, mcp_server_id, mcp_tool}
    defaults = Column(_JSON, nullable=True)
    # 步骤编排：list[dict]
    scenario_flow = Column(_JSON, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
