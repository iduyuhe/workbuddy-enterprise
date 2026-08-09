"""MCP 连接器 Pydantic schemas（本地定义，对齐 API_CONTRACT.md §5）。"""
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


class MCPServerCreate(BaseModel):
    name: str
    transport: str = "stdio"  # stdio / sse / http
    endpoint: Optional[str] = None
    command: Optional[str] = None
    project_id: Optional[UUID] = None
    secret_ref: Optional[str] = None  # 凭据引用，明文不落库


class MCPServerOut(BaseModel):
    id: UUID
    name: str
    transport: str
    endpoint: Optional[str] = None
    command: Optional[str] = None
    project_id: Optional[UUID] = None
    status: str


class MCPToolOut(BaseModel):
    name: str
    schema_json: Optional[dict] = None


class MCPCallRequest(BaseModel):
    project_id: Optional[UUID] = None
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPCallResponse(BaseModel):
    ok: bool
    result: Optional[Any] = None
    error: Optional[str] = None
