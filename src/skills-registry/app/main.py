"""skills-registry — 兼容 Anthropic Skills 文件式规范的技能注册中心。"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as skills_router
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="workbuddy-ent-skills-registry",
    version="1.0.0",
    description="技能注册/版本/列表/调用元数据（兼容 Anthropic Skills 规范）",
    lifespan=lifespan,
)

app.include_router(skills_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "skills-registry"}
