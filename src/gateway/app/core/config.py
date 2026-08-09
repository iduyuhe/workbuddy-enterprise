"""gateway configuration: downstream service URLs + JWT verify settings."""
from __future__ import annotations

import os


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


AUTH_SERVICE_URL = _env("AUTH_SERVICE_URL", "http://localhost:8002")
MODEL_GATEWAY_URL = _env("MODEL_GATEWAY_URL", "http://localhost:8001")
KB_SERVICE_URL = _env("KB_SERVICE_URL", "http://localhost:8005")
SKILLS_SERVICE_URL = _env("SKILLS_SERVICE_URL", "http://localhost:8003")
MCP_SERVICE_URL = _env("MCP_SERVICE_URL", "http://localhost:8004")
AUDIT_SERVICE_URL = _env("AUDIT_SERVICE_URL", "http://localhost:8006")

JWT_SECRET = _env("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = _env("JWT_ALGORITHM", "HS256")
