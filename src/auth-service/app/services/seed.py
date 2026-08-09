"""Idempotent seed: built-in roles, permissions, admin user, default project."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import SEED_ADMIN_PASSWORD, SEED_ADMIN_USERNAME
from app.core.security import hash_password
from app.models.org import Project
from app.models.rbac import (
    Permission,
    Role,
    User,
    role_permissions,
    user_roles,
)

# permission codes used across the platform (API_CONTRACT + ARCHITECTURE §6.2)
PERMISSIONS: dict[str, str] = {
    "chat:send": "发送对话请求",
    "kb:read": "知识库检索/读取",
    "kb:write": "知识库写入/入库",
    "skill:read": "技能读取",
    "skill:invoke": "技能调用",
    "mcp:read": "MCP 工具读取",
    "mcp:call": "MCP 工具调用",
    "audit:read": "查看审计日志",
    "audit:export": "导出审计日志",
    "user:read": "查看用户",
    "user:write": "管理用户",
    "role:read": "查看角色",
    "role:write": "管理角色/权限",
    "project:read": "查看项目",
    "project:write": "管理项目",
    "model:read": "查看模型路由",
    "model:admin": "管理模型/密钥",
}

ROLE_PERMS: dict[str, list[str]] = {
    "admin": list(PERMISSIONS.keys()),  # all
    "member": ["chat:send", "kb:read", "kb:write", "skill:read", "skill:invoke",
               "mcp:read", "mcp:call", "project:read", "model:read"],
    "auditor": ["audit:read", "audit:export", "user:read", "project:read"],
}


def seed(db: Session) -> None:
    # permissions
    perm_rows: dict[str, Permission] = {}
    for code, desc in PERMISSIONS.items():
        existing = db.execute(select(Permission).where(Permission.code == code)).scalar_one_or_none()
        if existing:
            perm_rows[code] = existing
        else:
            p = Permission(code=code, description=desc)
            db.add(p)
            db.flush()
            perm_rows[code] = p

    # roles
    role_rows: dict[str, Role] = {}
    for name, codes in ROLE_PERMS.items():
        role = db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
        if not role:
            role = Role(name=name, description=f"内置角色 {name}", builtin=True)
            db.add(role)
            db.flush()
        role_rows[name] = role
        # (re)assign permissions
        db.execute(role_permissions.delete().where(role_permissions.c.role_id == role.id))
        for code in codes:
            db.execute(
                role_permissions.insert().values(
                    role_id=role.id, permission_id=perm_rows[code].id
                )
            )

    # admin user
    admin = db.execute(
        select(User).where(User.username == SEED_ADMIN_USERNAME)
    ).scalar_one_or_none()
    if not admin:
        admin = User(
            username=SEED_ADMIN_USERNAME,
            display_name="Administrator",
            email="admin@workbuddy.local",
            idp="local",
            status="active",
            password_hash=hash_password(SEED_ADMIN_PASSWORD),
        )
        db.add(admin)
        db.flush()

    # default project owned by admin
    project = db.execute(select(Project).where(Project.name == "default")).scalar_one_or_none()
    if not project:
        project = Project(name="default", description="默认项目", owner_id=admin.id)
        db.add(project)
        db.flush()

    # assign admin role platform-wide (project_id NULL) to admin user
    db.execute(
        user_roles.insert().values(
            user_id=admin.id, role_id=role_rows["admin"].id, project_id=None
        ).prefix_with("OR IGNORE")  # sqlite no-op guard; postgres uses ON CONFLICT below
    ) if False else None
    # safe cross-db bind (upsert-like): delete then insert
    db.execute(
        user_roles.delete().where(
            (user_roles.c.user_id == admin.id)
            & (user_roles.c.role_id == role_rows["admin"].id)
            & (user_roles.c.project_id.is_(None))
        )
    )
    db.execute(
        user_roles.insert().values(
            user_id=admin.id, role_id=role_rows["admin"].id, project_id=None
        )
    )
    # also add admin as member of default project with admin role
    db.execute(
        user_roles.delete().where(
            (user_roles.c.user_id == admin.id)
            & (user_roles.c.role_id == role_rows["admin"].id)
            & (user_roles.c.project_id == project.id)
        )
    )
    db.execute(
        user_roles.insert().values(
            user_id=admin.id, role_id=role_rows["admin"].id, project_id=project.id
        )
    )

    db.commit()
