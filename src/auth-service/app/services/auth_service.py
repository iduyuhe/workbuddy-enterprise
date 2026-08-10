"""Local auth: verify credentials, issue/refresh JWT, user CRUD."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    LOCK_SECONDS,
    MAX_FAILED_LOGINS,
    PasswordPolicyError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models.rbac import Role, User
from app.services.rbac_service import get_user_roles


def authenticate(db: Session, username: str, password: str) -> User | None:
    """校验凭据；实现等保三级登录失败锁定（防暴力破解）。

    返回 User 表示成功；返回 None 表示失败（含已锁定）。锁定判定：
      - 已锁定且未到期 → 直接拒绝（不计数）
      - 凭据错误 → failed_login_count+1，达阈值则锁定 LOCK_SECONDS 并清零计数
      - 凭据正确 → 清零计数与锁定
    """
    import time

    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user or user.status != "active":
        return None
    # 已锁定且未到期
    if user.locked_until and int(time.time()) < user.locked_until:
        return None
    if not user.password_hash or not verify_password(password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = int(time.time()) + LOCK_SECONDS
            user.failed_login_count = 0
        db.commit()
        return None
    # 成功：复位
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    return user


def _projects_of(db: Session, user_id: str) -> list[str]:
    # user is member of projects via project_members OR owns projects; MVP: derive from user_roles project_ids
    from app.models.rbac import user_roles

    rows = db.execute(
        select(user_roles.c.project_id).where(user_roles.c.user_id == user_id)
    ).all()
    return [r[0] for r in rows if r[0]]


def issue_tokens(db: Session, user: User) -> dict:
    roles = list(dict.fromkeys(get_user_roles(db, user.id)))  # dedupe, keep order
    projects = list(dict.fromkeys(_projects_of(db, user.id)))
    access = create_access_token(
        user_id=user.id,
        username=user.username,
        roles=roles,
        projects=projects,
    )
    refresh = create_refresh_token(user.id)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "expires_in": 3600,
        "token_type": "Bearer",
    }


def refresh_tokens(db: Session, refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if payload.get("typ") != "refresh":
        raise ValueError("not a refresh token")
    user = db.get(User, payload["sub"])
    if not user or user.status != "active":
        raise ValueError("user not found")
    return issue_tokens(db, user)


def create_user(
    db: Session,
    *,
    username: str,
    password: str | None,
    display_name: str | None = None,
    email: str | None = None,
    idp: str = "local",
    role: str = "member",
    project_id: str | None = None,
) -> User:
    # 等保三级 · 身份鉴别：本地账号密码须满足复杂度策略
    if password and idp == "local":
        validate_password_strength(password)
    user = User(
        username=username,
        display_name=display_name,
        email=email,
        idp=idp,
        password_hash=hash_password(password) if password else None,
    )
    db.add(user)
    db.flush()
    # bind role (default 'member') to project
    role_row = db.execute(select(Role).where(Role.name == role)).scalar_one_or_none()
    if role_row:
        from app.models.rbac import user_roles

        db.execute(
            user_roles.insert().values(
                user_id=user.id, role_id=role_row.id, project_id=project_id
            )
        )
    db.commit()
    db.refresh(user)
    return user
