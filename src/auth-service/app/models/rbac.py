"""RBAC + identity ORM models (ARCHITECTURE §4: users/roles/permissions/user_roles)."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db import Base

# Use PG UUID when on postgres, else String fallback (sqlite local dev).
try:
    from sqlalchemy.dialects import postgresql  # noqa: F401

    _UUID = PG_UUID(as_uuid=False)
except Exception:  # pragma: no cover
    _UUID = String(36)


def _pk() -> Column:
    return Column(_UUID, primary_key=True, default=lambda: str(uuid.uuid4()))


# association tables
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", _UUID, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", _UUID, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", _UUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", _UUID, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", _UUID, nullable=True, primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = _pk()
    external_id = Column(String(128), nullable=True)
    username = Column(String(128), unique=True, nullable=False, index=True)
    display_name = Column(String(256), nullable=True)
    email = Column(String(256), unique=True, nullable=True)
    idp = Column(String(64), default="local")
    password_hash = Column(String(256), nullable=True)  # local accounts only
    status = Column(String(16), default="active")
    created_at = Column(Text, default=lambda: __import__("datetime").datetime.utcnow().isoformat())

    roles = relationship(
        "Role",
        secondary=user_roles,
        primaryjoin=id == user_roles.c.user_id,
        secondaryjoin="Role.id == user_roles.c.role_id",
        viewonly=True,
    )


class Role(Base):
    __tablename__ = "roles"

    id = _pk()
    name = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(256), nullable=True)
    builtin = Column(Boolean, default=False)

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        lazy="selectin",
    )


class Permission(Base):
    __tablename__ = "permissions"

    id = _pk()
    code = Column(String(128), unique=True, nullable=False, index=True)
    description = Column(String(256), nullable=True)
