# knowledge-service — 企业知识库 RAG

## 职责
- 文档 ingest：MinerU 解析 → bge-m3 切片向量 → Qdrant 入库。
- 检索：vector search + Reranker 重排，返回带分数片段。
- 知识库/文档元数据管理（PostgreSQL），向量按 `kb_id` 隔离（Qdrant）。

## 技术栈
Python 3.11 + FastAPI + SQLAlchemy + qdrant-client + sentence-transformers(bge-m3) + LangChain(可选) + Pydantic。

## 运行方式
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005
```
环境变量：`DATABASE_URL`、`QDRANT_URL`、`EMBEDDING_MODEL=bge-m3`、`RERANKER_MODEL`、`MINERU_HOME`。

## 实现团队
AI / AgentOps（RAG 链路）+ 后端（元数据/隔离）。
