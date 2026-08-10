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
AGENT_SERVICE_URL = _env("AGENT_SERVICE_URL", "http://localhost:8007")
AGENT_CHAT_ENABLED = _env("AGENT_CHAT_ENABLED", "false").lower() in ("1", "true", "yes", "on")

JWT_SECRET = _env("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = _env("JWT_ALGORITHM", "HS256")

# ===== 等保三级 · 入侵防范 / 传输安全 =====
RATE_LIMIT_PER_MINUTE = int(_env("RATE_LIMIT_PER_MINUTE", "120"))
RATE_LIMIT_ENABLED = _env("RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes", "on")
SECURITY_HEADERS_ENABLED = _env("SECURITY_HEADERS_ENABLED", "true").lower() in ("1", "true", "yes", "on")
