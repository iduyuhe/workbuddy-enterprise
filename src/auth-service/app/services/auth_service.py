"""Local auth: verify credentials, issue/refresh JWT, user CRUD."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.rbac import Role, User
from app.services.rbac_service import get_user_roles


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user or user.status != "active":
        return None
    if not user.password_hash or not verify_password(password, user.password_hash):
        return None
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
