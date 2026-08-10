"""audit-service configuration."""
from __future__ import annotations

import os

from shared.db.connect import normalize_database_url

DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./audit.db"))

# 等保三级 · 数据保密性：审计明细 SM4 加密存储密钥（须 16 字节；生产从密钥管理注入）
AUDIT_ENC_KEY = os.getenv("AUDIT_ENC_KEY", "wb-audit-sm4-key").encode("utf-8")
