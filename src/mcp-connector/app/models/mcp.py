"""MCP 连接器 ORM 模型，对应 ARCHITECTURE.md §4 mcp_servers / mcp_tools / mcp_credentials。"""
import uuid
from sqlalchemy import (
    String, Text, JSON, UUID, Boolean, ForeignKey, DateTime, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    transport: Mapped[str] = mapped_column(String(16), default="stdio")  # stdio / sse / http
    endpoint: Mapped[str | None] = mapped_column(Text)
    command: Mapped[str | None] = mapped_column(Text)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tools: Mapped[list["MCPTool"]] = relationship(
        "MCPTool", back_populates="server", cascade="all, delete-orphan"
    )
    credentials: Mapped[list["MCPCredential"]] = relationship(
        "MCPCredential", back_populates="server", cascade="all, delete-orphan"
    )


class MCPTool(Base):
    __tablename__ = "mcp_tools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    server: Mapped["MCPServer"] = relationship("MCPServer", back_populates="tools")


class MCPCredential(Base):
    __tablename__ = "mcp_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE")
    )
    key: Mapped[str | None] = mapped_column(String(128))
    secret_ref: Mapped[str | None] = mapped_column(Text)  # 指向密钥管理，明文不落库
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    server: Mapped["MCPServer"] = relationship("MCPServer", back_populates="credentials")
