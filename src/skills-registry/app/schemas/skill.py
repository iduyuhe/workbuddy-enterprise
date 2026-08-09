"""Skills Pydantic schemas（本地定义，对齐 API_CONTRACT.md §4）。"""
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    slug: str
    name: str
    storage_path: str
    project_id: Optional[UUID] = None
    is_public: bool = False
    description: Optional[str] = None


class SkillOut(BaseModel):
    id: UUID
    slug: str
    name: str
    version: str
    description: Optional[str] = None
    manifest: Optional[dict] = None
    storage_path: Optional[str] = None
    project_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    is_public: bool = False


class SkillDetail(SkillOut):
    pass


class SkillInvokeRequest(BaseModel):
    project_id: Optional[UUID] = None
    args: dict[str, Any] = Field(default_factory=dict)


class SkillInvokeResponse(BaseModel):
    invocation_id: UUID
    skill_id: UUID
    endpoint: str
    status: str  # dispatched
    args: dict[str, Any] = Field(default_factory=dict)


class SkillVersionCreate(BaseModel):
    manifest: dict
    version: Optional[str] = None  # 省略则自动递增 patch 版本


class SkillVersionOut(BaseModel):
    id: UUID
    skill_id: UUID
    version: str
    manifest: Optional[dict] = None
    created_at: Optional[str] = None
