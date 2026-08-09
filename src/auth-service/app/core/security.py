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
    REFRESH_TOKEN_EXPIRE_DAYS,
)


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
