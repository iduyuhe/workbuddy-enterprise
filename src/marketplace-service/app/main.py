"""marketplace-service — 生态市场（技能/连接器/专家包 的交易与分发）。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as marketplace_router
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="workbuddy-ent-marketplace",
    version="1.0.0",
    description="生态市场：包发布、浏览筛选、版本分发、租户安装、评价评分、运营统计",
    lifespan=lifespan,
)

app.include_router(marketplace_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "marketplace-service"}
