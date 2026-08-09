"""knowledge-service — 企业知识库 RAG：MinerU→bge-m3→Qdrant，检索+重排。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as kb_router
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="workbuddy-ent-knowledge-service",
    version="1.0.0",
    description="文档 ingest（解析→切片→向量→Qdrant）、向量检索 + 重排、知识库/文档元数据",
    lifespan=lifespan,
)

app.include_router(kb_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "knowledge-service"}
