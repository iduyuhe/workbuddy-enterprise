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

# ===== OIDC 单点登录（可选；未配置 OIDC_ISSUER 则禁用）=====
OIDC_ISSUER = os.getenv("OIDC_ISSUER")  # e.g. https://keycloak.example.com/realms/workbuddy
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")
OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "http://localhost:8000/api/auth/callback")
OIDC_SCOPES = os.getenv("OIDC_SCOPES", "openid email profile")
OIDC_FRONTEND_REDIRECT = os.getenv("OIDC_FRONTEND_REDIRECT", "http://localhost:3000")
OIDC_ENABLED = bool(OIDC_ISSUER and OIDC_CLIENT_ID)
