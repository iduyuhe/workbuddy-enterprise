"""mcp-connector REST 路由，对齐 API_CONTRACT.md §5。"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import HEADER_PROJECT_ID
from app.core.db import get_db
from app.models.mcp import MCPServer, MCPTool, MCPCredential
from app.schemas.mcp import (
    MCPCallRequest, MCPCallResponse, MCPServerCreate, MCPServerOut, MCPToolOut,
)
from app.services.mcp_client import call_tool, list_tools

router = APIRouter()


def _to_out(server: MCPServer) -> MCPServerOut:
    return MCPServerOut(
        id=server.id, name=server.name, transport=server.transport,
        endpoint=server.endpoint, command=server.command,
        project_id=server.project_id, status=server.status,
    )


@router.post("/mcp/servers", response_model=MCPServerOut, status_code=201)
def register_server(payload: MCPServerCreate, request: Request, db: Session = Depends(get_db)):
    if payload.transport not in ("stdio", "sse", "http"):
        raise HTTPException(status_code=400, detail="transport must be stdio/sse/http")
    if payload.transport in ("sse", "http") and not payload.endpoint:
        raise HTTPException(status_code=400, detail="endpoint required for sse/http transport")

    server = MCPServer(
        name=payload.name, transport=payload.transport,
        endpoint=payload.endpoint, command=payload.command,
        project_id=payload.project_id, status="active",
    )
    db.add(server)
    db.commit()
    db.refresh(server)

    # 凭据仅存引用（secret_ref），明文不落库
    if payload.secret_ref:
        db.add(MCPCredential(server_id=server.id, key=payload.name, secret_ref=payload.secret_ref))
        db.commit()
    return _to_out(server)


@router.get("/mcp/servers")
def list_servers(
    project_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
):
    stmt = select(MCPServer)
    if project_id is not None:
        stmt = stmt.where(MCPServer.project_id == project_id)
    rows = db.scalars(stmt.order_by(MCPServer.created_at.desc())).all()
    return {"items": [_to_out(s).model_dump() for s in rows], "total": len(rows)}


@router.get("/mcp/servers/{server_id}", response_model=MCPServerOut)
def get_server(server_id: uuid.UUID, db: Session = Depends(get_db)):
    server = db.get(MCPServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="mcp server not found")
    return _to_out(server)


@router.delete("/mcp/servers/{server_id}")
def delete_server(server_id: uuid.UUID, db: Session = Depends(get_db)):
    server = db.get(MCPServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="mcp server not found")
    # 级联清理工具清单与凭据引用
    db.query(MCPCredential).filter(MCPCredential.server_id == server_id).delete()
    db.query(MCPTool).filter(MCPTool.server_id == server_id).delete()
    db.delete(server)
    db.commit()
    return {"deleted": str(server_id)}


@router.post("/mcp/servers/{server_id}/sync")
async def sync_tools(server_id: uuid.UUID, db: Session = Depends(get_db)):
    server = db.get(MCPServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="mcp server not found")

    if server.transport == "stdio":
        # TODO(阶段2): 通过子进程拉起 stdio MCP server 并执行 tools/list 握手
        raise HTTPException(status_code=501, detail="stdio sync not implemented in MVP (TODO)")

    if not server.endpoint:
        raise HTTPException(status_code=400, detail="server has no endpoint")

    try:
        tools = await list_tools(server.endpoint)
    except Exception as e:  # 网络/协议错误，保持服务可观测
        raise HTTPException(status_code=502, detail=f"sync failed: {e}")

    # 全量覆盖该 server 的工具清单
    db.query(MCPTool).filter(MCPTool.server_id == server_id).delete()
    for t in tools:
        name = t.get("name")
        schema_json = {
            "description": t.get("description"),
            "inputSchema": t.get("inputSchema"),
        }
        db.add(MCPTool(server_id=server_id, name=name, schema_json=schema_json))
    db.commit()
    return {"server_id": str(server_id), "tools": len(tools)}


@router.get("/mcp/servers/{server_id}/tools")
def list_tools_route(
    server_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
):
    server = db.get(MCPServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="mcp server not found")
    rows = db.scalars(select(MCPTool).where(MCPTool.server_id == server_id)).all()
    return {
        "items": [MCPToolOut(name=r.name, schema_json=r.schema_json).model_dump() for r in rows],
        "total": len(rows),
    }


@router.post("/mcp/servers/{server_id}/tools/{tool_name}/call", response_model=MCPCallResponse)
async def call_tool_route(
    server_id: uuid.UUID, tool_name: str, payload: MCPCallRequest, db: Session = Depends(get_db)
):
    server = db.get(MCPServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="mcp server not found")

    if server.transport == "stdio":
        # TODO(阶段2): 通过 stdio 子进程转发 tools/call
        raise HTTPException(status_code=501, detail="stdio call not implemented in MVP (TODO)")

    if not server.endpoint:
        raise HTTPException(status_code=400, detail="server has no endpoint")

    try:
        result = await call_tool(server.endpoint, tool_name, payload.arguments)
        return MCPCallResponse(ok=True, result=result)
    except Exception as e:
        return MCPCallResponse(ok=False, error=str(e))
