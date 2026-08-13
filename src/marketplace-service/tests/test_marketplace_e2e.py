"""生态市场 真实 PG e2e 验证。

运行（仓库根 -> 经 socks5 推送前本地验证）：
    PYTHONPATH=src:src/marketplace-service \
    DATABASE_URL=postgresql+psycopg2://wbadmin:wbsecret@localhost:5432/workbuddy \
    pytest src/marketplace-service/tests/test_marketplace_e2e.py -v

全部断言走真实 PostgreSQL，无 mock。
"""
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# 确保 shared 与 app 可导入
# 文件位于 src/marketplace-service/tests/，向上 3 层到 src
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SVC = os.path.join(ROOT, "marketplace-service")
sys.path.insert(0, SVC)              # 提供 `app` 包
sys.path.insert(0, ROOT)            # 提供 `shared` 包（shared 位于 src/shared）

from app.core.db import engine  # noqa: E402
from app.models.package import (  # noqa: E402
    Package, PackageVersion, PackageInstall, PackageReview,
)
from app.main import app  # noqa: E402

PGURL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://wbadmin:wbsecret@localhost:5432/workbuddy",
)


@pytest.fixture(scope="module")
def client():
    # 触发 lifespan -> init_db (alembic upgrade head, 幂等)
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db():
    # 每个用例前清空 4 表，保证隔离（按 FK 顺序删）
    with engine.begin() as conn:
        for t in ("package_reviews", "package_installs", "package_versions", "packages"):
            conn.execute(text(f"DELETE FROM {t}"))
    yield


def _headers(tenant: uuid.UUID | None = None, user: uuid.UUID | None = None):
    h = {}
    if tenant is not None:
        h["X-Tenant-Id"] = str(tenant)
    if user is not None:
        h["X-User-Id"] = str(user)
    return h


def _publish(c, **kw):
    base = dict(slug="openai-connector", name="OpenAI Connector",
                package_type="connector", publisher="acme",
                summary="OpenAI 兼容连接器", tags=["llm", "openai"],
                price_model="free", is_public=True)
    base.update(kw)
    return c.post("/packages", json=base, headers=_headers(uuid.uuid4(), uuid.uuid4()))


# --------------------------------------------------------------------------- #
def test_publish_and_dup_slug(client):
    r = _publish(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == "openai-connector"
    assert body["package_type"] == "connector"
    assert body["version"] == "0.1.0"
    assert body["install_count"] == 0

    # 重复 slug -> 409
    r2 = _publish(client)
    assert r2.status_code == 409


def test_browse_filters_and_sort(client):
    t1, t2 = uuid.uuid4(), uuid.uuid4()
    _publish(client, slug="skill-rag", name="RAG Skill", package_type="skill",
             tags=["rag", "nlp"], price_model="free")
    _publish(client, slug="expert-fin", name="Finance Expert", package_type="expert",
             publisher="bankco", tags=["finance"], price_model="paid", price_cents=9900)
    _publish(client, slug="conn-slack", name="Slack Connector", package_type="connector",
             tags=["chat"], price_model="free")

    # type 筛选
    r = client.get("/packages?type=skill")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["package_type"] == "skill"

    # tag 筛选
    r = client.get("/packages?tag=rag")
    assert len(r.json()["items"]) == 1 and r.json()["items"][0]["slug"] == "skill-rag"

    # price_model 筛选
    r = client.get("/packages?price_model=paid")
    assert len(r.json()["items"]) == 1 and r.json()["items"][0]["slug"] == "expert-fin"

    # 关键词搜索
    r = client.get("/packages?q=slack")
    assert len(r.json()["items"]) == 1

    # 排序：newest（最后发布的 expert-fin 应排第一）
    r = client.get("/packages?sort=newest")
    assert r.json()["items"][0]["slug"] == "conn-slack"


def test_version_publish_and_dedup(client):
    _publish(client, slug="vpkg", name="Ver Pkg", package_type="skill")
    # 加版本
    r = client.post("/packages/" + str(_pid(client, "vpkg")) + "/versions",
                    json=dict(version="0.2.0", changelog="feat", download_url="http://x/v0.2.0",
                              artifact_hash="sha256:abc"))
    assert r.status_code == 201, r.text
    assert r.json()["version"] == "0.2.0"
    # 最新版本推进
    assert client.get("/packages/" + str(_pid(client, "vpkg"))).json()["version"] == "0.2.0"
    # 重复版本 -> 409
    r2 = client.post("/packages/" + str(_pid(client, "vpkg")) + "/versions",
                     json=dict(version="0.2.0"))
    assert r2.status_code == 409
    # 版本详情
    r3 = client.get("/packages/" + str(_pid(client, "vpkg")) + "/versions/0.2.0")
    assert r3.status_code == 200 and r3.json()["download_url"] == "http://x/v0.2.0"


def test_tenant_install_isolation_and_count(client):
    _publish(client, slug="ipkg", name="Install Pkg", package_type="skill")
    pid = _pid(client, "ipkg")
    T1, T2 = uuid.uuid4(), uuid.uuid4()

    # 缺 X-Tenant-Id -> 400
    r = client.post(f"/packages/{pid}/install")
    assert r.status_code == 400

    # T1 安装
    r = client.post(f"/packages/{pid}/install", headers=_headers(T1))
    assert r.status_code == 201 and r.json()["install_count"] == 1
    # T1 重复安装 -> 幂等，count 不变
    r = client.post(f"/packages/{pid}/install", headers=_headers(T1))
    assert r.json()["install_count"] == 1 and r.json()["created"] is False
    # T2 安装 -> count=2（多租户隔离的获取记录）
    r = client.post(f"/packages/{pid}/install", headers=_headers(T2))
    assert r.json()["install_count"] == 2

    # 卸载 T1 -> count=1
    r = client.delete(f"/packages/{pid}/install", headers=_headers(T1))
    assert r.json()["install_count"] == 1


def test_private_package_tenant_isolation(client):
    r = _publish(client, slug="priv", name="Private Pkg", package_type="skill",
                is_public=False, tenant_id=str(uuid.UUID(int=1)))  # 归属租户 0000...01
    pid = r.json()["id"]
    owner = uuid.UUID(int=1)
    other = uuid.uuid4()

    # 公共浏览：私有包对其它租户不可见
    r = client.get("/packages", headers=_headers(other))
    slugs = [i["slug"] for i in r.json()["items"]]
    assert "priv" not in slugs

    # 归属租户在 'all' 可见
    r = client.get("/packages", headers=_headers(owner))
    assert "priv" in [i["slug"] for i in r.json()["items"]]

    # scope=mine 仅归属租户自己的
    r = client.get("/packages?scope=mine", headers=_headers(owner))
    assert "priv" in [i["slug"] for i in r.json()["items"]]
    r = client.get("/packages?scope=mine", headers=_headers(other))
    assert r.json()["total"] == 0

    # 其它租户按 id 直取私有包 -> 404
    r = client.get(f"/packages/{pid}", headers=_headers(other))
    assert r.status_code == 404


def test_reviews_recompute_avg(client):
    _publish(client, slug="rpkg", name="Review Pkg", package_type="skill")
    pid = _pid(client, "rpkg")
    T1, T2 = uuid.uuid4(), uuid.uuid4()
    r = client.post(f"/packages/{pid}/reviews",
                    json=dict(rating=4, title="good", body="works"), headers=_headers(T1))
    assert r.status_code == 201
    r = client.post(f"/packages/{pid}/reviews",
                    json=dict(rating=5), headers=_headers(T2))
    assert r.status_code == 201

    body = client.get(f"/packages/{pid}").json()
    assert body["rating_count"] == 2
    assert abs(body["rating_avg"] - 4.5) < 1e-6

    # 评价列表
    r = client.get(f"/packages/{pid}/reviews")
    assert r.status_code == 200 and len(r.json()) == 2


def test_marketplace_stats(client):
    _publish(client, slug="s1", name="S1", package_type="skill")
    _publish(client, slug="c1", name="C1", package_type="connector")
    _publish(client, slug="e1", name="E1", package_type="expert")
    pid = _pid(client, "s1")
    # 安装一次 -> install_count=1
    client.post(f"/packages/{pid}/install", headers=_headers(uuid.uuid4()))

    r = client.get("/marketplace/stats")
    assert r.status_code == 200
    s = r.json()
    assert s["total_packages"] == 3
    assert s["by_type"].get("skill") == 1 and s["by_type"].get("connector") == 1 and s["by_type"].get("expert") == 1
    assert s["total_installs"] == 1
    assert any(p["slug"] == "s1" for p in s["top_packages"])


def _pid(client, slug):
    r = client.get(f"/packages?q={slug}")
    for it in r.json()["items"]:
        if it["slug"] == slug:
            return it["id"]
    raise AssertionError(f"package {slug} not found")
