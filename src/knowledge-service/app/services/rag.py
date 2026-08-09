"""RAG 业务：ingest 流水线（解析→切片→向量化→入库）+ 检索 + 简易重排。

ingest 在后台任务中执行，文档状态 pending→parsing→indexed/failed。
"""
import os
import uuid

from sqlalchemy.orm import Session

from app.core.config import CHUNK_OVERLAP, CHUNK_SIZE, UPLOAD_ROOT
from app.core.db import SessionLocal
from app.models.knowledge import Document, KnowledgeBase
from app.services.chunker import chunk_blocks
from app.services.embedder import get_embedder
from app.services.parser import parse_file
from app.services.vector_store import get_vector_store


def _new_id() -> str:
    return str(uuid.uuid4())


def run_ingest(document_id: uuid.UUID, file_path: str) -> None:
    """后台 ingest：解析→切片→向量化→写入向量库，更新文档状态。"""
    db: Session = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if not document:
            return
        kb = db.get(KnowledgeBase, document.kb_id)
        if not kb or not kb.collection:
            document.status = "failed"
            document.meta_json = {"error": "kb/collection missing"}
            db.commit()
            return

        document.status = "parsing"
        db.commit()

        try:
            blocks = parse_file(file_path)
            chunks = chunk_blocks(blocks, CHUNK_SIZE, CHUNK_OVERLAP)
            if not chunks:
                document.status = "failed"
                document.meta_json = {"error": "no extractable text"}
                db.commit()
                return

            embedder = get_embedder()
            texts = [c["text"] for c in chunks]
            vectors = embedder.encode(texts)

            store = get_vector_store()
            store.ensure_collection(kb.collection, embedder.dim)
            points = []
            for c, vec in zip(chunks, vectors):
                points.append({
                    "id": _new_id(),
                    "vector": vec,
                    "payload": {
                        "document_id": str(document.id),
                        "kb_id": str(kb.id),
                        "content": c["text"],
                        "meta": c.get("meta", {}),
                    },
                })
            store.upsert(kb.collection, points)

            document.status = "indexed"
            document.chunk_count = len(chunks)
            document.meta_json = {"chunks": len(chunks)}
            db.commit()
        except Exception as e:  # noqa: BLE001
            document.status = "failed"
            document.meta_json = {"error": str(e)}
            db.commit()
        finally:
            # 清理临时落盘文件
            try:
                os.remove(file_path)
            except OSError:
                pass
    finally:
        db.close()


def search(
    kb: KnowledgeBase, query: str, top_k: int,
    rerank: bool, score_threshold: float | None,
) -> list[dict]:
    if not kb.collection:
        return []
    embedder = get_embedder()
    vector = embedder.encode([query])[0]
    store = get_vector_store()
    results = store.search(kb.collection, vector, top_k, kb_id=kb.id)

    if score_threshold is not None:
        results = [r for r in results if r["score"] >= score_threshold]

    # 简易重排：rerank=True 时按 score 降序（已默认）。
    # TODO(阶段2): 接入 cross-encoder reranker（如 bge-reranker-v2-m3）做精排，
    # 以及查询改写 / 多路召回融合。
    results.sort(key=lambda r: -r["score"])
    return results
