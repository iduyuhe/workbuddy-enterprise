"""JWT verification + principal extraction for the gateway."""
from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request

from app.core.config import JWT_ALGORITHM, JWT_SECRET


@dataclass
class Principal:
    user_id: str
    username: str
    roles: list[str]
    project_id: str | None = None


def authenticate(request: Request) -> Principal:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid token")
    if payload.get("typ") != "access":
        raise HTTPException(status_code=401, detail="not an access token")
    return Principal(
        user_id=payload["sub"],
        username=payload.get("username", ""),
        roles=payload.get("roles", []),
        project_id=payload.get("prj"),
    )
