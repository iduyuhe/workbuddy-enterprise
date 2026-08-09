"""Common API contracts shared across WorkBuddy Enterprise services.

Mirrors docs/API_CONTRACT.md §通用约定:
  - unified error body: { error: { code, message, req_id } }
  - pagination:        { items, total, page, size }
  - ISO-8601 UTC timestamps
"""
from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    req_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class Page(BaseModel, Generic[T]):
    """Generic paginated response (page is 1-based)."""

    items: List[T] = []
    total: int = 0
    page: int = 1
    size: int = 20


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 3600
    token_type: str = "Bearer"


class JWTPayload(BaseModel):
    """Shape of the JWT we issue (HS256, PyJWT)."""

    sub: str  # user id
    username: str
    roles: List[str] = []
    projects: List[str] = []
    prj: Optional[str] = None  # active project id
    typ: str = "access"  # access | refresh


class AuditEvent(BaseModel):
    """Internal audit event payload (gateway -> audit-service)."""

    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    project_id: Optional[str] = None
    action: str
    resource: Optional[str] = None
    req_id: Optional[str] = None
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    ip: Optional[str] = None
    detail: Optional[dict] = None
