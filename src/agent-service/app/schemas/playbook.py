"""智能体剧本 Pydantic schemas（对齐 API_CONTRACT.md §6 草案）。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class PlaybookCreate(BaseModel):
    name: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    # 默认接线：{kb_id, skill_id, mcp_server_id, mcp_tool}
    defaults: dict[str, Any] = Field(default_factory=dict)
    # 步骤编排：list[dict]
    scenario_flow: list[dict[str, Any]] = Field(default_factory=list)
    is_public: bool = False
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None


class PlaybookUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    defaults: Optional[dict[str, Any]] = None
    scenario_flow: Optional[list[dict[str, Any]]] = None
    is_public: Optional[bool] = None


class PlaybookOut(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    name: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    defaults: dict[str, Any] = Field(default_factory=dict)
    scenario_flow: list[dict[str, Any]] = Field(default_factory=list)
    is_public: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
