"""数据库连接 URL 归一化（信创适配核心）。

目标：让平台通过配置 `DATABASE_URL` 即可指向不同数据库，包括信创数据库，
而无需改动业务代码。原理：
  - KingBaseES / openGauss 与 PostgreSQL 协议兼容 → 直接复用 `postgresql+psycopg2` 方言；
  - 达梦(DM) 使用专用 `dm://` 方案（部署时需安装 `dmPython` 驱动）；
  - SQLite / PostgreSQL / MySQL 原样透传。

所有服务的 `db.py` 在读取 `DATABASE_URL` 后都经本函数归一化，确保信创库「配置即适配」。
"""

from __future__ import annotations

from urllib.parse import urlparse

# PostgreSQL 兼容的信创库：复用 PG 方言驱动
_PG_COMPAT = {"kingbase", "kingbasees", "opengauss", "opengaussjdbc"}
# 达梦：专用驱动，URL 方案保持 dm://
_DM = {"dm", "dameng"}
# 原生支持、原样透传
_NATIVE = {"sqlite", "postgresql", "postgresql+psycopg2", "mysql", "mysql+pymysql"}

SUPPORTED_SCHEMES = _NATIVE | _PG_COMPAT | _DM


def normalize_database_url(url: str | None) -> str | None:
    """归一化数据库 URL。

    - KingBase/openGauss → postgresql+psycopg2://（PG 协议兼容）
    - 达梦 → 保持 dm://（部署侧装 dmPython）
    - 未知方案 → 抛 ValueError（fail-fast，避免静默连错库）
    """
    if not url:
        return url
    if "://" not in url:
        return url
    scheme = url.split("://", 1)[0].lower()
    if scheme in _PG_COMPAT:
        return url.replace(scheme + "://", "postgresql+psycopg2://", 1)
    if scheme in _DM:
        return url  # dmPython 驱动原生支持 dm://
    if scheme not in SUPPORTED_SCHEMES:
        raise ValueError(f"unsupported DATABASE_URL scheme: {scheme!r} (supported: {sorted(SUPPORTED_SCHEMES)})")
    return url


def is_xinchuang(url: str | None) -> bool:
    """该 URL 是否指向信创数据库（达梦 / KingBase / openGauss）。"""
    if not url or "://" not in url:
        return False
    scheme = url.split("://", 1)[0].lower()
    return scheme in (_DM | _PG_COMPAT)


def dialect_name(url: str | None) -> str:
    """返回归一化后的 SQLAlchemy 方言名（用于日志/分支判断）。"""
    norm = normalize_database_url(url) or ""
    scheme = norm.split("://", 1)[0].lower()
    if scheme.startswith("postgresql"):
        return "postgresql"
    return scheme
