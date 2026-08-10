"""Password hashing + JWT issue/verify for auth-service."""
from __future__ import annotations

import base64
import hashlib
import os
import time
import uuid

import jwt

from .config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET,
    LOCK_MINUTES,
    MAX_FAILED_LOGINS,
    PASSWORD_MIN_LEN,
    PASSWORD_REQUIRE_COMPLEXITY,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

# 锁定秒数（供 auth_service 直接引用，避免重复换算）
LOCK_SECONDS = LOCK_MINUTES * 60


# ---------- password hashing (self-contained, no extra deps) ----------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return "pbkdf2_sha256$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return base64.b64encode(dk).decode() == hash_b64
    except Exception:
        return False


# ---------- 密码复杂度策略（等保三级 · 身份鉴别） ----------
class PasswordPolicyError(ValueError):
    """密码不满足复杂度策略。"""


def validate_password_strength(password: str) -> None:
    """校验密码复杂度；不满足抛出 PasswordPolicyError（message 含具体原因）。

    策略（环境变量可配）：
      - 长度 >= PASSWORD_MIN_LEN（默认 8）
      - 当 PASSWORD_REQUIRE_COMPLEXITY 开启（默认）：须同时含 大写/小写/数字/特殊字符
    DEV 环境可设 PASSWORD_REQUIRE_COMPLEXITY=false 放宽以便测试。
    """
    if not password or len(password) < PASSWORD_MIN_LEN:
        raise PasswordPolicyError(f"password too short (min {PASSWORD_MIN_LEN} chars)")
    if PASSWORD_REQUIRE_COMPLEXITY:
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        missing = []
        if not has_lower:
            missing.append("小写字母")
        if not has_upper:
            missing.append("大写字母")
        if not has_digit:
            missing.append("数字")
        if not has_special:
            missing.append("特殊字符")
        if missing:
            raise PasswordPolicyError("password must contain: " + "/".join(missing))


# ---------- JWT ----------
def create_access_token(
    *,
    user_id: str,
    username: str,
    roles: list[str],
    projects: list[str],
    project_id: str | None = None,
) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "roles": roles,
        "projects": projects,
        "prj": project_id,
        "typ": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "typ": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
