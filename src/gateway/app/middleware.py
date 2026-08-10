"""等保三级 · 入侵防范与传输安全中间件。

- RateLimitMiddleware：按客户端 IP 做固定窗口限流，超额返回 429（防爆破/DoS）。
- SecurityHeadersMiddleware：注入等保推荐的 HTTP 安全响应头。
两者均可通过环境变量关闭，便于 DEV 调试。
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_PER_MINUTE,
    SECURITY_HEADERS_ENABLED,
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = RATE_LIMIT_PER_MINUTE, enabled: bool = RATE_LIMIT_ENABLED):
        super().__init__(app)
        self.calls = calls
        self.enabled = enabled
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_ip(self, request: Request) -> str:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)
        ip = self._client_ip(request)
        now = time.time()
        window = self._hits[ip]
        # 仅保留最近 60s 内的请求
        self._hits[ip] = [t for t in window if now - t < 60]
        if len(self._hits[ip]) >= self.calls:
            retry = 60 - int(now - self._hits[ip][0])
            return JSONResponse(
                status_code=429,
                content={"detail": "too many requests"},
                headers={"Retry-After": str(max(retry, 1))},
            )
        self._hits[ip].append(now)
        return await call_next(request)


_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; object-src 'none'",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, enabled: bool = SECURITY_HEADERS_ENABLED):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if self.enabled:
            for k, v in _SECURITY_HEADERS.items():
                response.headers.setdefault(k, v)
        return response
