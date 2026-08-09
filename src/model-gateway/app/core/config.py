"""model-gateway configuration."""
from __future__ import annotations

import os


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


DATABASE_URL = _env("DATABASE_URL", "sqlite:///./model_gateway.db")

VLLM_API_BASE = _env("VLLM_API_BASE", "http://localhost:8080/v1")
DEEPSEEK_API_BASE = _env("DEEPSEEK_API_BASE", "http://localhost:8081/v1")
CLAUDE_API_BASE = _env("CLAUDE_API_BASE", "")  # optional

# When a real provider is unreachable, fall back to a built-in mock stream so the
# MVP loop is runnable without a GPU. Set ENABLE_MOCK=false to disable.
ENABLE_MOCK = _env("ENABLE_MOCK", "true").lower() in ("1", "true", "yes")

ACCESS_TOKEN_EXPIRE_MINUTES = int(_env("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
JWT_SECRET = _env("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = _env("JWT_ALGORITHM", "HS256")

# static model catalog (context windows); merged with DB-seeded providers
MODEL_CATALOG = {
    "qwen3-235b": {"provider": "vllm", "context_window": 32768},
    "qwen3-32b": {"provider": "vllm", "context_window": 32768},
    "deepseek-v3": {"provider": "sglang", "context_window": 64000},
    "claude": {"provider": "claude", "context_window": 200000},
}
