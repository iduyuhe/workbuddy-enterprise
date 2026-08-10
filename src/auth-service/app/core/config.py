"""auth-service configuration (env-driven)."""
from __future__ import annotations

import os

from shared.db.connect import normalize_database_url


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


DATABASE_URL = normalize_database_url(_env("DATABASE_URL", "sqlite:///./auth.db"))

JWT_SECRET = _env("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = _env("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(_env("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(_env("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

SEED_ADMIN_USERNAME = _env("SEED_ADMIN_USERNAME", "admin")
SEED_ADMIN_PASSWORD = _env("SEED_ADMIN_PASSWORD", "admin123")

# ===== 等保三级 · 身份鉴别 =====
# 密码复杂度策略：最小长度 + 是否要求含大小写/数字/特殊字符
PASSWORD_MIN_LEN = int(_env("PASSWORD_MIN_LEN", "8"))
PASSWORD_REQUIRE_COMPLEXITY = _env("PASSWORD_REQUIRE_COMPLEXITY", "true").lower() in ("1", "true", "yes", "on")
# 登录失败锁定：连续失败 MAX_FAILED_LOGINS 次锁定 LOCK_MINUTES 分钟（防暴力破解）
MAX_FAILED_LOGINS = int(_env("MAX_FAILED_LOGINS", "5"))
LOCK_MINUTES = int(_env("LOCK_MINUTES", "15"))

# ===== OIDC 单点登录（可选；未配置 OIDC_ISSUER 则禁用）=====
OIDC_ISSUER = os.getenv("OIDC_ISSUER")  # e.g. https://keycloak.example.com/realms/workbuddy
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")
OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "http://localhost:8000/api/auth/callback")
OIDC_SCOPES = os.getenv("OIDC_SCOPES", "openid email profile")
OIDC_FRONTEND_REDIRECT = os.getenv("OIDC_FRONTEND_REDIRECT", "http://localhost:3000")
OIDC_ENABLED = bool(OIDC_ISSUER and OIDC_CLIENT_ID)
