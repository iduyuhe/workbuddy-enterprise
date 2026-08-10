"""Admin CRUD: users / roles(+permissions) / projects(+members)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Principal, get_principal, require_admin
from app.models.org import Project, ProjectMember
from app.models.rbac import Permission, Role, User, role_permissions, user_roles

router = APIRouter(tags=["admin"])


# ---------------- users ----------------
class CreateUserReq(BaseModel):
    username: str
    password: str | None = None
    display_name: str | None = None
    email: str | None = None
    idp: str = "local"
    role: str = "member"
    project_id: str | None = None


@router.get("/users")
def list_users(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
    tenant_id: str | None = Query(None),
    page: int = 1,
    size: int = 20,
):
    stmt = select(User)
    # 多租户：按租户隔离
    if tenant_id:
        stmt = stmt.where(User.tenant_id == tenant_id)
    total = len(db.execute(stmt.with_only_columns(User.id)).all())
    rows = db.execute(
        stmt.order_by(User.username).limit(size).offset((page - 1) * size)
    ).scalars().all()
    items = [
        {"id": u.id, "username": u.username, "display_name": u.display_name,
         "email": u.email, "idp": u.idp, "status": u.status, "tenant_id": u.tenant_id}
        for u in rows
    ]
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("/users")
def create_user(
    body: CreateUserReq,
    _: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.services.auth_service import create_user as _create_user

    if db.execute(select(User).where(User.username == body.username)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="username already exists")
    user = _create_user(
        db,
        username=body.username,
        password=body.password,
        display_name=body.display_name,
        email=body.email,
        idp=body.idp,
        role=body.role,
        project_id=body.project_id,
    )
    return {"id": user.id, "username": user.username}


@router.get("/users/{user_id}")
def get_user(user_id: str, _: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "idp": user.idp,
        "status": user.status,
    }


# ---------------- roles ----------------
class CreateRoleReq(BaseModel):
    name: str
    description: str | None = None


class RolePermsReq(BaseModel):
    permission_codes: list[str]


@router.get("/roles")
def list_roles(_: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    rows = db.execute(select(Role).order_by(Role.name)).scalars().all()
    items = [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "builtin": r.builtin,
            "permissions": [p.code for p in r.permissions],
        }
        for r in rows
    ]
    return {"items": items, "total": len(items), "page": 1, "size": len(items)}


@router.post("/roles")
def create_role(
    body: CreateRoleReq,
    _: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.execute(select(Role).where(Role.name == body.name)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="role already exists")
    role = Role(name=body.name, description=body.description, builtin=False)
    db.add(role)
    db.commit()
    return {"id": role.id, "name": role.name}


@router.put("/roles/{role_id}/permissions")
def set_role_permissions(
    role_id: str,
    body: RolePermsReq,
    _: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="role not found")
    db.execute(role_permissions.delete().where(role_permissions.c.role_id == role_id))
    for code in body.permission_codes:
        perm = db.execute(select(Permission).where(Permission.code == code)).scalar_one_or_none()
        if not perm:
            raise HTTPException(status_code=400, detail=f"unknown permission: {code}")
        db.execute(role_permissions.insert().values(role_id=role_id, permission_id=perm.id))
    db.commit()
    return {"id": role_id, "permissions": body.permission_codes}


# ---------------- projects ----------------
class CreateProjectReq(BaseModel):
    name: str
    description: str | None = None


class AddMemberReq(BaseModel):
    user_id: str
    role: str = "member"
    project_id: str | None = None  # override; defaults to the path project


@router.get("/projects")
def list_projects(_: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    rows = db.execute(select(Project).order_by(Project.name)).scalars().all()
    items = [
        {"id": p.id, "name": p.name, "description": p.description, "owner_id": p.owner_id}
        for p in rows
    ]
    return {"items": items, "total": len(items), "page": 1, "size": len(items)}


@router.post("/projects")
def create_project(
    body: CreateProjectReq,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    proj = Project(name=body.name, description=body.description, owner_id=principal.user_id)
    db.add(proj)
    db.flush()
    # bind creator as admin on the new project
    admin_role = db.execute(select(Role).where(Role.name == "admin")).scalar_one_or_none()
    if admin_role:
        db.execute(
            user_roles.insert().values(
                user_id=principal.user_id, role_id=admin_role.id, project_id=proj.id
            )
        )
    db.commit()
    return {"id": proj.id, "name": proj.name}


@router.post("/projects/{project_id}/members")
def add_member(
    project_id: str,
    body: AddMemberReq,
    _: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    proj = db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="project not found")
    role = db.execute(select(Role).where(Role.name == body.role)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail=f"unknown role: {body.role}")
    # upsert membership
    db.execute(
        user_roles.delete().where(
            (user_roles.c.user_id == body.user_id)
            & (user_roles.c.role_id == role.id)
            & (user_roles.c.project_id == project_id)
        )
    )
    db.execute(
        user_roles.insert().values(
            user_id=body.user_id, role_id=role.id, project_id=project_id
        )
    )
    # also project_members
    db.execute(
        ProjectMember.__table__.delete().where(
            (ProjectMember.project_id == project_id) & (ProjectMember.user_id == body.user_id)
        )
    )
    db.add(ProjectMember(project_id=project_id, user_id=body.user_id))
    db.commit()
    return {"project_id": project_id, "user_id": body.user_id, "role": body.role}
