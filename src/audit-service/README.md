# audit-service (:8006)

审计服务：接收调用级审计事件落库，支持查询与 CSV 导出（API_CONTRACT §6）。

## 端点
- `POST /audit/events`  写入（网关异步调用）
- `GET  /audit/events`  查询（按 project_id / actor_id / action / 时间范围）
- `GET  /audit/export`  CSV 导出

下游信任网关注入的 `X-User-Id` / `X-Project-Id`。查询/导出默认要求内部调用（带 X-User-Id）。

## 运行
```bash
cd src/audit-service
pip install -r requirements.txt
uvicorn app.main:app --port 8006 --reload
```
