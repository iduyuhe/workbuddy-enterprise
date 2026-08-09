"""Generic reverse-proxy for /api/* with JWT auth + RBAC + X-User-* injection + audit."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.client import client_ip
from app.core.config import (
    AUDIT_SERVICE_URL,
    AUTH_SERVICE_URL,
    KB_SERVICE_URL,
    MCP_SERVICE_URL,
    MODEL_GATEWAY_URL,
    SKILLS_SERVICE_URL,
)
from app.core.rbac import check_rbac
from app.core.security import authenticate
from app.services.audit_client import send_audit
from shared.schemas.common import AuditEvent
from shared.schemas.errors import error_response, new_req_id

router = APIRouter()

# service routing: strip the leading "/api" then forward to the base
SERVICE_BY_PREFIX = {
    "/api/auth": AUTH_SERVICE_URL,
    "/api/v1": MODEL_GATEWAY_URL,
    "/api/kb": KB_SERVICE_URL,
    "/api/skills": SKILLS_SERVICE_URL,
    "/api/mcp": MCP_SERVICE_URL,
    "/api/audit": AUDIT_SERVICE_URL,
}

# public (no auth / no rbac) endpoints
PUBLIC = {
    ("POST", "/api/auth/login/local"),
    ("GET", "/api/auth/login"),
    ("POST", "/api/auth/callback"),
}


def _resolve_base(path: str) -> str:
    for prefix, base in SERVICE_BY_PREFIX.items():
        if path == prefix or path.startswith(prefix + "/"):
            return base
    return AUTH_SERVICE_URL


def derive_rbac_action(path: str, method: str) -> str | None:
    """Map a gateway path+method to an RBAC action, or None to skip checks."""
    if (method, path) in PUBLIC:
        return None
    if path == "/api/auth/rbac/check":  # internal-only
        return None

    if path.startswith("/api/auth/users"):
        res = "user"
    elif path.startswith("/api/auth/roles"):
        res = "role"
    elif path.startswith("/api/auth/projects"):
        res = "project"
    elif path.startswith("/api/v1"):
        res = "model"
    elif path.startswith("/api/kb"):
        res = "kb"
    elif path.startswith("/api/skills"):
        res = "skill"
    elif path.startswith("/api/mcp"):
        res = "mcp"
    elif path.startswith("/api/audit"):
        res = "audit"
    else:
        return None

    if path.endswith("/export"):
        return f"{res}:export"
    if method == "GET":
        return f"{res}:read"
    return f"{res}:write"


def _inject_headers(request: Request, principal) -> dict:
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "authorization")
    }
    headers["X-User-Id"] = principal.user_id
    headers["X-Project-Id"] = principal.project_id or ""
    return headers


@router.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(request: Request, path: str):
    full_path = "/api/" + path
    # route chat explicitly to the SSE-aware handler
    if full_path == "/api/v1/chat":
        from app.api.chat import chat_entry

        return await chat_entry(request)

    # auth
    if (request.method, full_path) not in PUBLIC:
        principal = authenticate(request)
    else:
        # public endpoints still forwarded (e.g. login) without identity
        principal = None

    action = derive_rbac_action(full_path, request.method)
    if action and principal is not None:
        allowed = await check_rbac(request.app.state.http, action, principal.user_id, principal.project_id)
        if not allowed:
            return error_response(403, "RBAC_DENIED", f"action {action} not allowed", new_req_id())

    base = _resolve_base(full_path)
    target_path = full_path[4:]  # strip /api
    target = base.rstrip("/") + target_path
    fwd_headers = _inject_headers(request, principal) if principal else dict(request.headers)
    fwd_headers.pop("host", None)
    fwd_headers.pop("content-length", None)

    client = request.app.state.http
    req_id = new_req_id()
    ip = client_ip(request)
    body = await request.body()

    try:
        resp = await client.request(
            request.method,
            target,
            params=request.query_params,
            headers=fwd_headers,
            content=body,
            timeout=60,
        )
    except Exception as e:  # upstream unreachable / timeout
        return error_response(502, "UPSTREAM_ERROR", f"{full_path} -> {target}: {e}", req_id)

    # async audit (fire-and-forget)
    if principal is not None:
        await send_audit(
            client,
            AuditEvent(
                actor_id=principal.user_id,
                actor_name=principal.username,
                project_id=principal.project_id,
                action=action or "proxy",
                resource=full_path,
                req_id=req_id,
                ip=ip,
            ),
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
        media_type=resp.headers.get("content-type"),
    )
