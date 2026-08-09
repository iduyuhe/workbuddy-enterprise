"""auth-service configuration (env-driven)."""
from __future__ import annotations

import os


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


DATABASE_URL = _env("DATABASE_URL", "sqlite:///./auth.db")

JWT_SECRET = _env("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = _env("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(_env("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(_env("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

SEED_ADMIN_USERNAME = _env("SEED_ADMIN_USERNAME", "admin")
SEED_ADMIN_PASSWORD = _env("SEED_ADMIN_PASSWORD", "admin123")
