"""生态市场 ORM 模型：包 / 版本 / 租户安装(获取) / 评价评分。"""
import uuid
from sqlalchemy import (
    String, Text, Boolean, JSON, Integer, Float, UUID, ForeignKey, DateTime,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

# PG 用 jsonb（支持 @> 包含查询，供 tag 筛选）；sqlite 回退 json
JSONType = JSON().with_variant(JSONB, "postgresql")


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    # 包类型：skill(技能) / connector(连接器) / expert(专家包)
    package_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    publisher: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(String(280))
    description: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(String(60))
    # 计费模式：free / paid / subscription
    price_model: Mapped[str] = mapped_column(String(20), default="free", nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="CNY", nullable=False)
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    categories: Mapped[list] = mapped_column(JSONType, default=list)
    homepage: Mapped[str | None] = mapped_column(String(512))
    repository: Mapped[str | None] = mapped_column(String(512))
    icon_url: Mapped[str | None] = mapped_column(String(512))
    supported_platforms: Mapped[list] = mapped_column(JSONType, default=list)
    # 当前最新版本
    version: Mapped[str] = mapped_column(String(32), default="0.1.0", nullable=False)
    # 派生统计（写入时维护，避免每次浏览全表聚合）
    install_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 是否发布到公共市场；False 且 tenant_id 非空则为租户私有预发布包
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # 多租户：私有包归属租户；公共包为 NULL
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["PackageVersion"]] = relationship(
        "PackageVersion", back_populates="package", cascade="all, delete-orphan"
    )
    installs: Mapped[list["PackageInstall"]] = relationship(
        "PackageInstall", back_populates="package", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["PackageReview"]] = relationship(
        "PackageReview", back_populates="package", cascade="all, delete-orphan"
    )


class PackageVersion(Base):
    __tablename__ = "package_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE")
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest: Mapped[dict | None] = mapped_column(JSONType)
    changelog: Mapped[str | None] = mapped_column(Text)
    # 制品分发地址（对象存储 / 包仓库 URL）
    download_url: Mapped[str | None] = mapped_column(String(512))
    # 制品完整性哈希（sha256），与平台国密/校验体系呼应
    artifact_hash: Mapped[str | None] = mapped_column(String(128))
    min_platform_version: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    package: Mapped["Package"] = relationship("Package", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("package_id", "version", name="uq_package_version"),
    )


class PackageInstall(Base):
    """租户对包的获取(安装)记录 —— 生态市场的「分发/交易」落地。"""

    __tablename__ = "package_installs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE")
    )
    # 多租户隔离：一个租户对同一个包仅一条获取记录（升级即更新版本）
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    installed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    package: Mapped["Package"] = relationship("Package", back_populates="installs")

    __table_args__ = (
        UniqueConstraint("package_id", "tenant_id", name="uq_package_tenant"),
    )


class PackageReview(Base):
    """用户评价与评分（1-5），支撑市场口碑与排序。"""

    __tablename__ = "package_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE")
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5
    title: Mapped[str | None] = mapped_column(String(160))
    body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    package: Mapped["Package"] = relationship("Package", back_populates="reviews")
