"""OIDC 授权码流程（Authorization Code + state/nonce 防 CSRF/重放）。

手写实现，仅依赖 httpx + PyJWT + cryptography（平台已装），兼容任意标准 IdP：
Keycloak / Azure AD / 飞书 / 企微 / Okta / Google Workspace。
未配置 OIDC_ISSUER 时整功能禁用（is_enabled() == False）。

注意：生产部署应配合 PKCE（S256）与短时效 state cookie；本 MVP 用 state cookie + nonce 校验。
"""
from __future__ import annotations

import uuid

import httpx
import jwt

from app.core.config import (
    OIDC_CLIENT_ID,
    OIDC_CLIENT_SECRET,
    OIDC_ISSUER,
    OIDC_REDIRECT_URI,
    OIDC_SCOPES,
)

_DISCOVERY_CACHE: dict[str, dict] = {}
_JWKS_CACHE: dict[str, dict] = {}


def is_enabled() -> bool:
    return bool(OIDC_ISSUER and OIDC_CLIENT_ID)


def discover(issuer: str | None = None) -> dict:
    """读取 IdP 的 .well-known/openid-configuration（带缓存）。"""
    issuer = issuer or OIDC_ISSUER
    if not issuer:
        raise RuntimeError("OIDC_ISSUER not configured")
    if issuer in _DISCOVERY_CACHE:
        return _DISCOVERY_CACHE[issuer]
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    resp = httpx.get(url, timeout=10.0)
    resp.raise_for_status()
    cfg = resp.json()
    _DISCOVERY_CACHE[issuer] = cfg
    return cfg


def build_authorize_url(state: str, nonce: str) -> str:
    from urllib.parse import urlencode

    disc = discover()
    params = {
        "client_id": OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": OIDC_SCOPES,
        "redirect_uri": OIDC_REDIRECT_URI,
        "state": state,
        "nonce": nonce,
    }
    return f"{disc['authorization_endpoint']}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """用授权码换 id_token / access_token。"""
    disc = discover()
    resp = httpx.post(
        disc["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": OIDC_REDIRECT_URI,
            "client_id": OIDC_CLIENT_ID,
            "client_secret": OIDC_CLIENT_SECRET or "",
        },
        headers={"Accept": "application/json"},
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()


def _jwk_to_public_key(jwk: dict):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

    n = int.from_bytes(jwt.utils.base64url_decode(jwk["n"]), "big")
    e = int.from_bytes(jwt.utils.base64url_decode(jwk["e"]), "big")
    return RSAPublicNumbers(e, n).public_key()


def verify_id_token(id_token: str, nonce: str | None = None) -> dict:
    """用 IdP jwks(RS256) 验证 id_token 签名/aud/iss，可选校验 nonce，返回 claims。"""
    disc = discover()
    jwks_uri = disc["jwks_uri"]
    if jwks_uri not in _JWKS_CACHE:
        r = httpx.get(jwks_uri, timeout=10.0)
        r.raise_for_status()
        _JWKS_CACHE[jwks_uri] = r.json()
    jwks = _JWKS_CACHE[jwks_uri]

    kid = jwt.get_unverified_header(id_token).get("kid")
    key = None
    for jwk in jwks.get("keys", []):
        if kid is None or jwk.get("kid") == kid:
            key = _jwk_to_public_key(jwk)
            break
    if key is None:
        raise RuntimeError("no matching JWK for id_token")

    claims = jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=OIDC_CLIENT_ID,
        issuer=disc.get("issuer") or OIDC_ISSUER,
        options={"verify_aud": True, "verify_iss": bool(disc.get("issuer"))},
    )
    if nonce is not None and claims.get("nonce") != nonce:
        raise RuntimeError("OIDC nonce mismatch")
    return claims


def new_state_nonce() -> tuple[str, str]:
    return uuid.uuid4().hex, uuid.uuid4().hex
