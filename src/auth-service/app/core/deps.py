"""Auth dependencies: resolve the caller principal (internal header OR JWT)."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models.rbac import User
from app.services.rbac_service import is_admin, get_user_roles


@dataclass
class Principal:
    user_id: str
    username: str
    roles: list[str]
    project_id: str | None = None


def get_principal(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> Principal:
    """Trust the gateway-injected header; fall back to verifying the JWT."""
    if x_user_id:
        user = db.get(User, x_user_id)
        if user:
            roles = get_user_roles(db, user.id)
            return Principal(user.id, user.username, roles, None)

    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = decode_token(token)
        except Exception:
            raise HTTPException(status_code=401, detail="invalid or expired token")
        if payload.get("typ") != "access":
            raise HTTPException(status_code=401, detail="not an access token")
        return Principal(
            user_id=payload["sub"],
            username=payload.get("username", ""),
            roles=payload.get("roles", []),
            project_id=payload.get("prj"),
        )
    raise HTTPException(status_code=401, detail="missing authentication")


def require_admin(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Principal:
    if not is_admin(db, principal.user_id):
        raise HTTPException(status_code=403, detail="admin role required")
    return principal
