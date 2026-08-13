"""mcp-connector — MCP Server 注册 / 工具清单同步 / 工具调用中继。"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as mcp_router
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="workbuddy-ent-mcp-connector",
    version="1.0.0",
    description="MCP Server 注册发现、工具清单同步、工具调用中继、凭据托管",
    lifespan=lifespan,
)

app.include_router(mcp_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-connector"}
