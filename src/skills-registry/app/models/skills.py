"""Skills ORM 模型，对应 ARCHITECTURE.md §4 skills / skill_versions 表。"""
import uuid
from sqlalchemy import (
    String, Text, Boolean, JSON, UUID, ForeignKey, DateTime, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="0.1.0")
    description: Mapped[str | None] = mapped_column(String(512))
    manifest: Mapped[dict | None] = mapped_column(JSON)           # SKILL.md 解析后的元数据
    storage_path: Mapped[str | None] = mapped_column(Text)        # 文件式技能存储路径
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    versions: Mapped[list["SkillVersion"]] = relationship(
        "SkillVersion", back_populates="skill", cascade="all, delete-orphan"
    )


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE")
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    skill: Mapped["Skill"] = relationship("Skill", back_populates="versions")
