"""skills-registry REST 路由，对齐 API_CONTRACT.md §4。"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import HEADER_PROJECT_ID, HEADER_USER_ID
from app.core.db import get_db
from app.models.skills import Skill, SkillVersion
from app.schemas.skill import (
    SkillCreate, SkillDetail, SkillInvokeRequest, SkillInvokeResponse,
    SkillOut, SkillVersionCreate, SkillVersionOut,
)
from app.services.skill_parser import (
    bump_version, load_manifest_from_storage, new_invocation_id,
)

router = APIRouter()


def _project_id_from_header(request: Request) -> Optional[uuid.UUID]:
    raw = request.headers.get(HEADER_PROJECT_ID)
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def _to_out(skill: Skill) -> SkillOut:
    return SkillOut(
        id=skill.id, slug=skill.slug, name=skill.name, version=skill.version,
        description=skill.description, manifest=skill.manifest,
        storage_path=skill.storage_path, project_id=skill.project_id,
        owner_id=skill.owner_id, is_public=skill.is_public,
    )


@router.post("/skills", response_model=SkillOut, status_code=201)
def create_skill(payload: SkillCreate, request: Request, db: Session = Depends(get_db)):
    # slug 唯一性
    if db.scalar(select(Skill).where(Skill.slug == payload.slug)):
        raise HTTPException(status_code=409, detail=f"slug '{payload.slug}' already exists")

    # 兼容 Anthropic Skills 规范：解析 SKILL.md 到 manifest
    manifest = load_manifest_from_storage(payload.storage_path)
    fm_name = (manifest or {}).get("name") if manifest else None
    description = payload.description or (manifest or {}).get("description") if manifest else None

    user_raw = request.headers.get(HEADER_USER_ID)
    owner_id = uuid.UUID(user_raw) if user_raw else None

    skill = Skill(
        slug=payload.slug,
        name=payload.name or (fm_name or payload.slug),
        version="0.1.0",
        description=description,
        manifest=manifest,
        storage_path=payload.storage_path,
        project_id=payload.project_id,
        owner_id=owner_id,
        is_public=payload.is_public,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    # 初始版本快照
    db.add(SkillVersion(skill_id=skill.id, version=skill.version, manifest=manifest))
    db.commit()
    return _to_out(skill)


@router.get("/skills")
def list_skills(
    project_id: Optional[uuid.UUID] = Query(None),
    scope: str = Query("all", pattern="^(all|mine)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Skill)
    if scope == "mine":
        # 仅返回归属该项目的技能
        if project_id is None:
            return {"items": [], "total": 0, "page": page, "size": size}
        stmt = stmt.where(Skill.project_id == project_id)
    else:  # all：本项目 + 平台共享(owner_id 在平台) + 公开
        conditions = [Skill.is_public.is_(True)]
        if project_id is not None:
            conditions.append(Skill.project_id == project_id)
        else:
            conditions.append(Skill.project_id.is_(None))
        stmt = stmt.where(or_(*conditions))

    total = len(db.scalars(stmt).all())
    rows = db.scalars(stmt.order_by(Skill.created_at.desc())
                      .offset((page - 1) * size).limit(size)).all()
    return {
        "items": [_to_out(s).model_dump() for s in rows],
        "total": total, "page": page, "size": size,
    }


@router.get("/skills/{skill_id}", response_model=SkillDetail)
def get_skill(skill_id: uuid.UUID, db: Session = Depends(get_db)):
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="skill not found")
    return _to_out(skill)


@router.post("/skills/{skill_id}/invoke", response_model=SkillInvokeResponse)
def invoke_skill(
    skill_id: uuid.UUID, payload: SkillInvokeRequest, db: Session = Depends(get_db)
):
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="skill not found")

    # MVP：仅返回调度元数据。实际执行由 agent-runtime(阶段2) 或网关编排消费。
    # TODO: 对接 agent-runtime 触发真实执行，并回写执行结果/审计事件。
    return SkillInvokeResponse(
        invocation_id=new_invocation_id(),
        skill_id=skill.id,
        endpoint=skill.storage_path or "",
        status="dispatched",
        args=payload.args,
    )


@router.post("/skills/{skill_id}/versions", response_model=SkillVersionOut, status_code=201)
def create_version(
    skill_id: uuid.UUID, payload: SkillVersionCreate, db: Session = Depends(get_db)
):
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="skill not found")

    version = payload.version or bump_version(skill.version)
    # 同版本去重
    if db.scalar(select(SkillVersion).where(
            SkillVersion.skill_id == skill_id, SkillVersion.version == version)):
        raise HTTPException(status_code=409, detail=f"version {version} exists")

    sv = SkillVersion(skill_id=skill.id, version=version, manifest=payload.manifest)
    db.add(sv)
    skill.version = version
    skill.manifest = payload.manifest
    db.commit()
    db.refresh(sv)
    return SkillVersionOut(
        id=sv.id, skill_id=sv.skill_id, version=sv.version,
        manifest=sv.manifest,
        created_at=sv.created_at.isoformat() if sv.created_at else None,
    )


@router.get("/skills/{skill_id}/versions", response_model=list[SkillVersionOut])
def list_versions(skill_id: uuid.UUID, db: Session = Depends(get_db)):
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="skill not found")
    rows = db.scalars(
        select(SkillVersion).where(SkillVersion.skill_id == skill_id)
        .order_by(SkillVersion.created_at.desc())
    ).all()
    return [
        SkillVersionOut(
            id=r.id, skill_id=r.skill_id, version=r.version, manifest=r.manifest,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]
