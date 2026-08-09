"""Model gateway ORM: model_providers / model_keys (BYOK, no plaintext key)."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text

from app.core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ModelProvider(Base):
    __tablename__ = "model_providers"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(64), nullable=False, unique=True)  # qwen3 / deepseek / claude
    kind = Column(String(32), nullable=False)  # vllm / sglang / bedrock / api
    base_url = Column(Text, nullable=True)
    default_model = Column(String(128), nullable=True)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)


class ModelKey(Base):
    __tablename__ = "model_keys"

    id = Column(String(36), primary_key=True, default=_uuid)
    provider_id = Column(String(36), ForeignKey("model_providers.id", ondelete="CASCADE"), nullable=True)
    label = Column(String(128), nullable=True)
    api_key_ref = Column(Text, nullable=True)  # secret-manager reference, NEVER plaintext
    scope = Column(String(16), default="tenant")  # tenant / user
    owner_id = Column(String(36), nullable=True)  # cross-service ref to auth-service users (no FK)
