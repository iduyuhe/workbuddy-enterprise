"""知识库 ORM 模型，对应 ARCHITECTURE.md §4 knowledge_bases / documents。

向量与 chunk 正文实际存于 Qdrant（payload 带 document_id / kb_id 供过滤）；
本表仅保存元数据与 Qdrant collection 名称。
"""
import uuid
from sqlalchemy import (
    String, Text, JSON, UUID, ForeignKey, DateTime, Integer, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    # 多租户：知识库归属租户
    tenant_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    embedding: Mapped[str] = mapped_column(String(64), default="bge-m3")
    collection: Mapped[str | None] = mapped_column(String(128))  # Qdrant collection 名
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="kb", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kb_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE")
    )
    title: Mapped[str | None] = mapped_column(String(256))
    source_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/parsing/indexed/failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    meta_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    kb: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")
