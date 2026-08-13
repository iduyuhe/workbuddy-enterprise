"""生态市场 REST 路由：发布 / 浏览筛选 / 版本 / 租户安装(获取) / 评价评分 / 统计。"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import cast, func, select, String as SAString
from sqlalchemy.orm import Session

from app.core.config import HEADER_TENANT_ID, HEADER_USER_ID
from app.core.db import get_db
from app.models.package import Package, PackageVersion, PackageInstall, PackageReview
from app.schemas.package import (
    BrowseResponse, MarketplaceStats, PackageCreate, PackageOut,
    PackageVersionCreate, PackageVersionOut, ReviewCreate, ReviewOut,
)

router = APIRouter()


# --------------------------------------------------------------------------- #
# 身份 / 租户头解析
# --------------------------------------------------------------------------- #
def _uuid_header(request: Request, key: str) -> Optional[uuid.UUID]:
    raw = request.headers.get(key)
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError):
        return None


def _to_out(p: Package) -> PackageOut:
    return PackageOut(
        id=p.id, slug=p.slug, name=p.name, package_type=p.package_type,
        publisher=p.publisher, summary=p.summary, description=p.description,
        license=p.license, price_model=p.price_model, price_cents=p.price_cents,
        currency=p.currency, tags=p.tags or [], categories=p.categories or [],
        homepage=p.homepage, repository=p.repository, icon_url=p.icon_url,
        supported_platforms=p.supported_platforms or [], version=p.version,
        install_count=p.install_count, rating_avg=round(p.rating_avg or 0.0, 2),
        rating_count=p.rating_count, is_public=p.is_public,
        tenant_id=p.tenant_id, owner_id=p.owner_id,
        created_at=p.created_at.isoformat() if p.created_at else None,
        updated_at=p.updated_at.isoformat() if p.updated_at else None,
    )


def _visible(p: Package, tenant_id: Optional[uuid.UUID]) -> bool:
    """私有包仅对归属租户可见；公共包对所有人可见。"""
    if p.is_public:
        return True
    if p.tenant_id is None:
        return True
    return tenant_id is not None and p.tenant_id == tenant_id


# --------------------------------------------------------------------------- #
# 发布
# --------------------------------------------------------------------------- #
@router.post("/packages", response_model=PackageOut, status_code=201)
def create_package(payload: PackageCreate, request: Request, db: Session = Depends(get_db)):
    if db.scalar(select(Package).where(Package.slug == payload.slug)):
        raise HTTPException(status_code=409, detail=f"slug '{payload.slug}' already exists")

    tenant_id = payload.tenant_id or _uuid_header(request, HEADER_TENANT_ID)
    owner_id = _uuid_header(request, HEADER_USER_ID)

    pkg = Package(
        slug=payload.slug, name=payload.name, package_type=payload.package_type,
        publisher=payload.publisher, summary=payload.summary, description=payload.description,
        license=payload.license, price_model=payload.price_model,
        price_cents=payload.price_cents, currency=payload.currency,
        tags=payload.tags, categories=payload.categories, homepage=payload.homepage,
        repository=payload.repository, icon_url=payload.icon_url,
        supported_platforms=payload.supported_platforms,
        version="0.1.0", is_public=payload.is_public,
        tenant_id=tenant_id, owner_id=owner_id,
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)

    # 初始版本快照
    db.add(PackageVersion(
        package_id=pkg.id, version=pkg.version, manifest={"name": payload.name},
    ))
    db.commit()
    return _to_out(pkg)


# --------------------------------------------------------------------------- #
# 浏览 / 筛选
# --------------------------------------------------------------------------- #
@router.get("/packages", response_model=BrowseResponse)
def browse_packages(
    package_type: Optional[str] = Query(None, alias="type"),
    tag: Optional[str] = None,
    license: Optional[str] = None,
    price_model: Optional[str] = None,
    publisher: Optional[str] = None,
    q: Optional[str] = None,
    scope: str = Query("all", pattern="^(all|mine)$"),
    sort: str = Query("popular", pattern="^(popular|newest|top_rated)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db),
):
    tenant_id = _uuid_header(request, HEADER_TENANT_ID) if request else None
    stmt = select(Package)

    # 可见性范围
    if scope == "mine":
        if tenant_id is None:
            return BrowseResponse(items=[], total=0, page=page, size=size)
        stmt = stmt.where(Package.tenant_id == tenant_id)
    else:  # all：公共包 + 当前租户私有包
        if tenant_id is not None:
            stmt = stmt.where(
                (Package.is_public.is_(True)) | (Package.tenant_id == tenant_id)
            )
        else:
            stmt = stmt.where(Package.is_public.is_(True))

    # 结构化筛选
    if package_type:
        stmt = stmt.where(Package.package_type == package_type)
    if license:
        stmt = stmt.where(Package.license == license)
    if price_model:
        stmt = stmt.where(Package.price_model == price_model)
    if publisher:
        stmt = stmt.where(Package.publisher == publisher)
    if tag:
        # 标签筛选：PG 用 jsonb 包含算子 @>；sqlite 回退 JSON 文本 LIKE（带引号防子串误匹配）
        if db.bind.dialect.name == "postgresql":
            stmt = stmt.where(Package.tags.op("@>")(func.jsonb_build_array(tag)))
        else:
            stmt = stmt.where(cast(Package.tags, SAString).like(f'%"{tag}"%'))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Package.name.ilike(like)) | (Package.slug.ilike(like))
            | (Package.summary.ilike(like)) | (Package.publisher.ilike(like))
            | (Package.description.ilike(like))
        )

    total = len(db.scalars(stmt).all())

    if sort == "newest":
        stmt = stmt.order_by(Package.created_at.desc())
    elif sort == "top_rated":
        stmt = stmt.order_by(Package.rating_avg.desc(), Package.rating_count.desc())
    else:  # popular
        stmt = stmt.order_by(Package.install_count.desc(), Package.created_at.desc())

    rows = db.scalars(stmt.offset((page - 1) * size).limit(size)).all()
    return BrowseResponse(
        items=[_to_out(r) for r in rows], total=total, page=page, size=size,
    )


@router.get("/packages/{package_id}", response_model=PackageOut)
def get_package(package_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    pkg = db.get(Package, package_id)
    if not pkg or not _visible(pkg, _uuid_header(request, HEADER_TENANT_ID)):
        raise HTTPException(status_code=404, detail="package not found")
    return _to_out(pkg)


# --------------------------------------------------------------------------- #
# 版本
# --------------------------------------------------------------------------- #
@router.post("/packages/{package_id}/versions", response_model=PackageVersionOut, status_code=201)
def add_version(package_id: uuid.UUID, payload: PackageVersionCreate, db: Session = Depends(get_db)):
    pkg = db.get(Package, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="package not found")
    if db.scalar(select(PackageVersion).where(
            PackageVersion.package_id == package_id, PackageVersion.version == payload.version)):
        raise HTTPException(status_code=409, detail=f"version {payload.version} exists")

    pv = PackageVersion(
        package_id=pkg.id, version=payload.version, manifest=payload.manifest,
        changelog=payload.changelog, download_url=payload.download_url,
        artifact_hash=payload.artifact_hash, min_platform_version=payload.min_platform_version,
    )
    db.add(pv)
    pkg.version = payload.version  # 推进最新版本
    db.commit()
    db.refresh(pv)
    return PackageVersionOut(
        id=pv.id, package_id=pv.package_id, version=pv.version, manifest=pv.manifest,
        changelog=pv.changelog, download_url=pv.download_url, artifact_hash=pv.artifact_hash,
        min_platform_version=pv.min_platform_version,
        created_at=pv.created_at.isoformat() if pv.created_at else None,
    )


@router.get("/packages/{package_id}/versions", response_model=list[PackageVersionOut])
def list_versions(package_id: uuid.UUID, db: Session = Depends(get_db)):
    pkg = db.get(Package, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="package not found")
    rows = db.scalars(
        select(PackageVersion).where(PackageVersion.package_id == package_id)
        .order_by(PackageVersion.created_at.desc())
    ).all()
    return [
        PackageVersionOut(
            id=r.id, package_id=r.package_id, version=r.version, manifest=r.manifest,
            changelog=r.changelog, download_url=r.download_url, artifact_hash=r.artifact_hash,
            min_platform_version=r.min_platform_version,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]


@router.get("/packages/{package_id}/versions/{version}", response_model=PackageVersionOut)
def get_version(package_id: uuid.UUID, version: str, db: Session = Depends(get_db)):
    pv = db.scalar(select(PackageVersion).where(
        PackageVersion.package_id == package_id, PackageVersion.version == version))
    if not pv:
        raise HTTPException(status_code=404, detail="version not found")
    return PackageVersionOut(
        id=pv.id, package_id=pv.package_id, version=pv.version, manifest=pv.manifest,
        changelog=pv.changelog, download_url=pv.download_url, artifact_hash=pv.artifact_hash,
        min_platform_version=pv.min_platform_version,
        created_at=pv.created_at.isoformat() if pv.created_at else None,
    )


# --------------------------------------------------------------------------- #
# 租户安装(获取/分发) —— 多租户隔离
# --------------------------------------------------------------------------- #
@router.post("/packages/{package_id}/install", status_code=201)
def install_package(package_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    tenant_id = _uuid_header(request, HEADER_TENANT_ID)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-Id header required")
    pkg = db.get(Package, package_id)
    if not pkg or not _visible(pkg, tenant_id):
        raise HTTPException(status_code=404, detail="package not found")

    existing = db.scalar(select(PackageInstall).where(
        PackageInstall.package_id == package_id, PackageInstall.tenant_id == tenant_id))
    if existing:
        existing.version = pkg.version
        created = False
    else:
        db.add(PackageInstall(
            package_id=pkg.id, tenant_id=tenant_id,
            installed_by=_uuid_header(request, HEADER_USER_ID), version=pkg.version))
        pkg.install_count = (pkg.install_count or 0) + 1
        created = True
    db.commit()
    return {
        "package_id": str(pkg.id), "tenant_id": str(tenant_id),
        "version": pkg.version, "install_count": pkg.install_count, "created": created,
    }


@router.delete("/packages/{package_id}/install")
def uninstall_package(package_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    tenant_id = _uuid_header(request, HEADER_TENANT_ID)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-Id header required")
    pkg = db.get(Package, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="package not found")
    existing = db.scalar(select(PackageInstall).where(
        PackageInstall.package_id == package_id, PackageInstall.tenant_id == tenant_id))
    if existing:
        db.delete(existing)
        pkg.install_count = max(0, (pkg.install_count or 0) - 1)
        db.commit()
    return {"package_id": str(pkg.id), "tenant_id": str(tenant_id),
            "install_count": pkg.install_count, "removed": existing is not None}


# --------------------------------------------------------------------------- #
# 评价 / 评分
# --------------------------------------------------------------------------- #
@router.get("/packages/{package_id}/reviews", response_model=list[ReviewOut])
def list_reviews(package_id: uuid.UUID, db: Session = Depends(get_db)):
    if not db.get(Package, package_id):
        raise HTTPException(status_code=404, detail="package not found")
    rows = db.scalars(
        select(PackageReview).where(PackageReview.package_id == package_id)
        .order_by(PackageReview.created_at.desc())
    ).all()
    return [
        ReviewOut(
            id=r.id, package_id=r.package_id, tenant_id=r.tenant_id,
            reviewer_id=r.reviewer_id, rating=r.rating, title=r.title, body=r.body,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]


@router.post("/packages/{package_id}/reviews", response_model=ReviewOut, status_code=201)
def add_review(package_id: uuid.UUID, payload: ReviewCreate, request: Request,
               db: Session = Depends(get_db)):
    pkg = db.get(Package, package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="package not found")
    if not (1 <= payload.rating <= 5):
        raise HTTPException(status_code=422, detail="rating must be 1..5")

    review = PackageReview(
        package_id=pkg.id, tenant_id=_uuid_header(request, HEADER_TENANT_ID),
        reviewer_id=payload.reviewer_id or _uuid_header(request, HEADER_USER_ID),
        rating=payload.rating, title=payload.title, body=payload.body,
    )
    db.add(review)
    db.commit()

    # 重算平均分（写入时维护，避免浏览时聚合）
    agg = db.execute(
        select(func.coalesce(func.avg(PackageReview.rating), 0),
               func.count(PackageReview.id))
        .where(PackageReview.package_id == package_id)
    ).first()
    pkg.rating_avg = float(agg[0] or 0.0)
    pkg.rating_count = int(agg[1] or 0)
    db.commit()
    db.refresh(review)
    return ReviewOut(
        id=review.id, package_id=review.package_id, tenant_id=review.tenant_id,
        reviewer_id=review.reviewer_id, rating=review.rating, title=review.title,
        body=review.body, created_at=review.created_at.isoformat() if review.created_at else None,
    )


# --------------------------------------------------------------------------- #
# 统计（市场运营看板）
# --------------------------------------------------------------------------- #
@router.get("/marketplace/stats", response_model=MarketplaceStats)
def marketplace_stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Package.id))) or 0
    total_installs = db.scalar(select(func.coalesce(func.sum(Package.install_count), 0))) or 0
    total_reviews = db.scalar(select(func.count(PackageReview.id))) or 0

    by_type_rows = db.execute(
        select(Package.package_type, func.count(Package.id))
        .group_by(Package.package_type)
    ).all()
    by_type = {t: c for t, c in by_type_rows}

    top = db.scalars(
        select(Package).order_by(Package.install_count.desc()).limit(5)
    ).all()
    top_packages = [
        {"id": str(p.id), "name": p.name, "slug": p.slug,
         "package_type": p.package_type, "install_count": p.install_count}
        for p in top
    ]
    return MarketplaceStats(
        total_packages=total, by_type=by_type, total_installs=int(total_installs),
        total_reviews=total_reviews, top_packages=top_packages,
    )
