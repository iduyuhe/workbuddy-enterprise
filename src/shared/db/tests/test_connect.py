"""连接 URL 归一化（信创适配）单元测试。"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from shared.db.connect import (
    dialect_name,
    is_xinchuang,
    normalize_database_url,
)


def test_kingbase_maps_to_postgresql():
    url = "kingbase://kb:pass@10.0.0.5:54321/workbuddy"
    assert normalize_database_url(url) == "postgresql+psycopg2://kb:pass@10.0.0.5:54321/workbuddy"
    assert dialect_name(url) == "postgresql"
    assert is_xinchuang(url) is True


def test_opengauss_maps_to_postgresql():
    url = "opengauss://og:pass@10.0.0.6:5432/workbuddy"
    assert normalize_database_url(url).startswith("postgresql+psycopg2://")
    assert is_xinchuang(url) is True


def test_dameng_passthrough():
    url = "dm://SYSDBA:SYSDBA@10.0.0.7:5236/workbuddy"
    assert normalize_database_url(url) == url  # 达梦专用驱动
    assert is_xinchuang(url) is True


def test_postgresql_passthrough():
    url = "postgresql+psycopg2://u:p@127.0.0.1:5432/db"
    assert normalize_database_url(url) == url
    assert is_xinchuang(url) is False
    assert dialect_name(url) == "postgresql"


def test_sqlite_passthrough():
    url = "sqlite:///./auth.db"
    assert normalize_database_url(url) == url
    assert is_xinchuang(url) is False


def test_unknown_scheme_raises():
    try:
        normalize_database_url("oracle://x/y")
        assert False, "should raise"
    except ValueError:
        pass


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
