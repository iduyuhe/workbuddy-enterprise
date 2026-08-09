"""Org asset models (ARCHITECTURE §4: projects/teams/experts)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, ForeignKey, String, Text

from app.core.db import Base
from app.models.rbac import _UUID, _pk


class Project(Base):
    __tablename__ = "projects"

    id = _pk()
    name = Column(String(128), nullable=False)
    description = Column(String(256), nullable=True)
    owner_id = Column(_UUID, ForeignKey("users.id"), nullable=True)
    created_at = Column(Text, default=lambda: __import__("datetime").datetime.utcnow().isoformat())


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = {"extend_existing": True}

    project_id = Column(_UUID, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(_UUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class Team(Base):
    __tablename__ = "teams"

    id = _pk()
    name = Column(String(128), nullable=False)
    project_id = Column(_UUID, ForeignKey("projects.id"), nullable=True)
    lead_id = Column(_UUID, ForeignKey("users.id"), nullable=True)
    created_at = Column(Text, default=lambda: __import__("datetime").datetime.utcnow().isoformat())


class Expert(Base):
    __tablename__ = "experts"

    id = _pk()
    name = Column(String(128), nullable=False)
    role = Column(String(128), nullable=True)
    description = Column(String(512), nullable=True)
    project_id = Column(_UUID, ForeignKey("projects.id"), nullable=True)
    owner_id = Column(_UUID, ForeignKey("users.id"), nullable=True)
    config_json = Column(Text, nullable=True)  # JSON string
    created_at = Column(Text, default=lambda: __import__("datetime").datetime.utcnow().isoformat())
