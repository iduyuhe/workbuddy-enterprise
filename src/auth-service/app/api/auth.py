"""Auth endpoints: local login, OIDC (TODO), refresh, me, RBAC check."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Principal, get_principal
from app.services.auth_service import authenticate, issue_tokens, refresh_tokens
from app.services.rbac_service import check_permission

router = APIRouter(tags=["auth"])


class LocalLoginReq(BaseModel):
    username: str
    password: str


class RefreshReq(BaseModel):
    refresh_token: str


class RbacCheckReq(BaseModel):
    user_id: str
    project_id: str | None = None
    action: str


@router.post("/auth/login/local")
def login_local(body: LocalLoginReq, db: Session = Depends(get_db)):
    user = authenticate(db, body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid username or password")
    return issue_tokens(db, user)


@router.get("/auth/login")
def oidc_login_start(redirect_uri: str | None = None):
    # TODO: implement OIDC authorization-code flow (Keycloak / Azure AD / 飞书 / 企微).
    # Return a 302 redirect to the IdP authorization endpoint.
    raise HTTPException(
        status_code=501,
        detail="OIDC login not implemented in MVP; use /auth/login/local. TODO: redirect to IdP.",
    )


@router.post("/auth/callback")
def oidc_callback(body: dict):
    # TODO: exchange code+state for id_token, then mint platform JWT.
    raise HTTPException(status_code=501, detail="OIDC callback not implemented in MVP. TODO.")


@router.post("/auth/token/refresh")
def token_refresh(body: RefreshReq, db: Session = Depends(get_db)):
    try:
        return refresh_tokens(db, body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/auth/me")
def auth_me(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    from app.services.auth_service import _projects_of

    return {
        "id": principal.user_id,
        "username": principal.username,
        "roles": principal.roles,
        "projects": _projects_of(db, principal.user_id),
    }


@router.post("/auth/rbac/check")
def rbac_check(body: RbacCheckReq, db: Session = Depends(get_db)):
    allowed = check_permission(db, body.user_id, body.project_id, body.action)
    # API_CONTRACT §1.6: 403 when not allowed
    if not allowed:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=403, content={"allowed": False})
    return {"allowed": True}
