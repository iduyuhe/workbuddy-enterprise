"""Auth endpoints: local login, OIDC (TODO), refresh, me, RBAC check."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import OIDC_FRONTEND_REDIRECT
from app.core.db import get_db
from app.core.deps import Principal, get_principal
from app.models.rbac import User
from app.services.auth_service import authenticate, create_user, issue_tokens, refresh_tokens
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
def oidc_login_start(response: Response, redirect_uri: str | None = None):
    from app.core import oidc

    if not oidc.is_enabled():
        raise HTTPException(status_code=501, detail="OIDC not configured; use /auth/login/local")
    state, nonce = oidc.new_state_nonce()
    url = oidc.build_authorize_url(state, nonce)
    # 直接把 cookie 写到返回的 RedirectResponse 上（避免 FastAPI 未合并 response 参数的 cookie）
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie("oidc_state", state, httponly=True, samesite="lax", path="/auth", max_age=600)
    if redirect_uri:
        resp.set_cookie("oidc_redirect", redirect_uri, httponly=True, samesite="lax", path="/auth", max_age=600)
    return resp


@router.get("/auth/callback")
def oidc_callback(request: Request, response: Response, db: Session = Depends(get_db)):
    from app.core import oidc

    if not oidc.is_enabled():
        raise HTTPException(status_code=501, detail="OIDC not configured")
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    cookie_state = request.cookies.get("oidc_state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="missing code/state")
    if not cookie_state or cookie_state != state:
        raise HTTPException(status_code=400, detail="state mismatch (possible CSRF)")
    try:
        tokens = oidc.exchange_code(code)
        id_token = tokens.get("id_token")
        if not id_token:
            raise HTTPException(status_code=502, detail="IdP did not return id_token")
        claims = oidc.verify_id_token(id_token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OIDC exchange failed: {e}")

    sub = claims.get("sub")
    email = claims.get("email")
    name = claims.get("name") or email or sub
    # 查找既有用户（按 external_id 或 email），否则按 OIDC 身份自动开通
    user = db.execute(select(User).where(User.idp == "oidc", User.external_id == sub)).scalar_one_or_none()
    if not user and email:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        user = create_user(
            db, username=email or sub, password=None,
            display_name=name, email=email, idp="oidc", role="member",
        )
        user.external_id = sub
        db.commit()
    jwt_out = issue_tokens(db, user)
    from urllib.parse import urlencode

    frontend_redirect = request.cookies.get("oidc_redirect") or f"{OIDC_FRONTEND_REDIRECT}/login"
    qs = urlencode({
        "access_token": jwt_out["access_token"],
        "refresh_token": jwt_out.get("refresh_token", ""),
    })
    response.delete_cookie("oidc_state", path="/auth")
    response.delete_cookie("oidc_redirect", path="/auth")
    return RedirectResponse(f"{frontend_redirect}?{qs}", status_code=302)


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
