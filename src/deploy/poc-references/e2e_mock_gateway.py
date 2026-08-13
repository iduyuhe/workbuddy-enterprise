"""端到端铺包实测用的「契约一致」轻量网关（非真实平台服务栈）。

仅用于在没有 Docker/k8s 的运行环境下，对 provision.py 做**真实 HTTP 层**端到端验证：
- 真实监听 8000，实现 provision.py 实际请求的 5 类端点 + 对应 DELETE；
- 剧本端点真实读写已验证的 PostgreSQL `agent_playbooks` 表（连 127.0.0.1:5432），
  用于联动验证 0004_playbook 迁移在铺包链路中真被使用；
- KB / 技能 / MCP 用内存集合模拟（返回真实 id），因它们需要 knowledge/skills/mcp
  服务的独立迁移与 Qdrant/Redis 等依赖，超出本环境范围；
- 每个请求的关键信息写入 mock_gateway.log（UTF-8），供验证读取。

真实平台铺包仍需 Docker/k8s 起全套微服务；本脚本验证的是 provision.py 脚本自身的
端点构造、租户 header 注入、logical_id→real_id 映射、嵌套 defaults 替换、state 落盘、
反向回滚全链路在真实网络层跑通。
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras as pg_extras
from fastapi import FastAPI, Request, UploadFile, File, Response
from fastapi.responses import JSONResponse

PG_URL = "postgresql://wbadmin:wbsecret@127.0.0.1:5432/workbuddy"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_gateway.log")

app = FastAPI(title="e2e-mock-gateway")

# 内存模拟存储（KB / 技能 / MCP）
kb_store: set[str] = set()
skill_store: set[str] = set()
mcp_store: set[str] = set()


def log(event: str, **kw) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {event} " + json.dumps(kw, ensure_ascii=False)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pg() -> psycopg2.extensions.connection:
    return psycopg2.connect(PG_URL)


def _check_tenant(headers) -> str | None:
    return headers.get("x-tenant-id") or headers.get("X-Tenant-Id")


# ---- 知识库 ----
@app.post("/api/kb/kb")
async def create_kb(req: Request):
    body = await req.json()
    kid = "kb_" + uuid.uuid4().hex[:12]
    kb_store.add(kid)
    log("CREATE_KB", id=kid, tenant=_check_tenant(req.headers), name=body.get("name"))
    return JSONResponse({"id": kid, "name": body.get("name")}, status_code=201)


@app.post("/api/kb/kb/{kid}/ingest")
async def ingest(kid: str, file: UploadFile = File(...)):
    log("INGEST_DOC", id=kid, filename=file.filename)
    return JSONResponse({"kb_id": kid, "ingested": file.filename}, status_code=200)


# ---- 技能 ----
@app.post("/api/skills/skills")
async def create_skill(req: Request):
    body = await req.json()
    sid = "skill_" + uuid.uuid4().hex[:12]
    skill_store.add(sid)
    log("CREATE_SKILL", id=sid, tenant=_check_tenant(req.headers), slug=body.get("slug"))
    return JSONResponse({"id": sid}, status_code=201)


# ---- MCP 连接器 ----
@app.post("/api/mcp/servers")
async def create_mcp(req: Request):
    body = await req.json()
    mid = "mcp_" + uuid.uuid4().hex[:12]
    mcp_store.add(mid)
    log("CREATE_MCP", id=mid, tenant=_check_tenant(req.headers), name=body.get("name"))
    return JSONResponse({"id": mid, "server_id": mid}, status_code=201)


@app.post("/api/mcp/servers/{mid}/sync")
async def sync_mcp(mid: str):
    log("SYNC_MCP", id=mid)
    return JSONResponse({"server_id": mid, "synced": True}, status_code=200)


# ---- 智能体剧本（真实读写 PG agent_playbooks）----
@app.post("/api/agent/playbooks")
async def create_playbook(req: Request):
    body = await req.json()
    pid = "pb_" + uuid.uuid4().hex[:12]
    tenant = body.get("tenant_id")
    project = body.get("project_id")
    defaults = body.get("defaults", {}) or {}
    scenario = body.get("scenario_flow", []) or []
    # 记录嵌套 logical_id 替换是否生效（真实 id 应以 kb_/skill_/mcp_ 前缀）
    log("CREATE_PLAYBOOK", id=pid, tenant=tenant, project=project, name=body.get("name"),
        model=body.get("model"),
        defaults_kb_id=defaults.get("kb_id"),
        defaults_skill_id=defaults.get("skill_id"),
        defaults_mcp_server_id=defaults.get("mcp_server_id"),
        defaults_mcp_tool=defaults.get("mcp_tool"))
    conn = pg()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO agent_playbooks "
            "(id, tenant_id, project_id, name, model, system_prompt, defaults, scenario_flow, is_public, created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, now(), now())",
            (pid, tenant, project, body.get("name"), body.get("model"),
             body.get("system_prompt"), pg_extras.Json(defaults), pg_extras.Json(scenario), False),
        )
        conn.commit()
    finally:
        conn.close()
    return JSONResponse({"id": pid}, status_code=201)


# ---- 删除（回滚）----
@app.delete("/api/kb/kb/{kid}")
async def del_kb(kid: str):
    kb_store.discard(kid)
    log("DELETE_KB", id=kid)
    return Response(status_code=204)


@app.delete("/api/skills/skills/{sid}")
async def del_skill(sid: str):
    skill_store.discard(sid)
    log("DELETE_SKILL", id=sid)
    return Response(status_code=204)


@app.delete("/api/mcp/servers/{mid}")
async def del_mcp(mid: str):
    mcp_store.discard(mid)
    log("DELETE_MCP", id=mid)
    return Response(status_code=204)


@app.delete("/api/agent/playbooks/{pid}")
async def del_playbook(pid: str):
    conn = pg()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM agent_playbooks WHERE id=%s", (pid,))
        conn.commit()
    finally:
        conn.close()
    log("DELETE_PLAYBOOK", id=pid)
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn

    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
