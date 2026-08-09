"""RBAC query helpers: resolve roles/permissions for a user and check actions."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rbac import Permission, Role, User, user_roles


def _role_rows(db: Session, user_id: str) -> list[tuple[str, str | None]]:
    """Return [(role_name, project_id), ...] for the user."""
    stmt = (
        select(Role.name, user_roles.c.project_id)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == user_id)
    )
    return [(r[0], r[1]) for r in db.execute(stmt).all()]


def get_user_roles(db: Session, user_id: str) -> list[str]:
    return [name for name, _ in _role_rows(db, user_id)]


def is_admin(db: Session, user_id: str) -> bool:
    return "admin" in get_user_roles(db, user_id)


def check_permission(db: Session, user_id: str, project_id: str | None, action: str) -> bool:
    """Project-scoped permission check.

    - platform admin (role 'admin' anywhere) -> allowed everything
    - otherwise the user must hold a role at `project_id` (or platform-level,
      project_id IS NULL) that grants the permission `action`.
    """
    rows = _role_rows(db, user_id)
    # platform-level admin shortcut
    if any(name == "admin" for name, pid in rows):
        return True

    relevant_role_ids = [
        rid
        for rid, pid in _role_rows_with_ids(db, user_id)
        if pid == project_id or pid is None
    ]
    if not relevant_role_ids:
        return False

    stmt = (
        select(Permission.code)
        .select_from(Role)
        .join(Role.permissions)
        .where(Role.id.in_(relevant_role_ids))
    )
    codes = {c[0] for c in db.execute(stmt).all()}
    return action in codes


def _role_rows_with_ids(db: Session, user_id: str) -> list[tuple[str, str | None]]:
    stmt = (
        select(Role.id, user_roles.c.project_id)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == user_id)
    )
    return [(r[0], r[1]) for r in db.execute(stmt).all()]
