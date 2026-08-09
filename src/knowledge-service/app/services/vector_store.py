"""向量存储抽象：Qdrant（生产） / InMemory（dev 默认）。

Qdrant 两种形态：
  - QDRANT_URL 指向独立服务端（生产集群）；
  - QDRANT_LOCAL_PATH 使用嵌入式本地引擎（免服务端，落盘持久化，单机/边缘生产可用）。
两者均通过 qdrant-client 真实引擎检索。InMemory 仅用于完全未配置时的单机演示。
统一接口：ensure_collection / upsert / search / delete_document / count。
"""
import os

import numpy as np

from app.core.config import QDRANT_API_KEY, QDRANT_URL, QDRANT_LOCAL_PATH


def _cosine(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


class InMemoryVectorStore:
    def __init__(self):
        # name -> {"dim": int, "points": [ {id, vector, payload} ]}
        self._store: dict[str, dict] = {}

    def ensure_collection(self, name: str, dim: int):
        self._store.setdefault(name, {"dim": dim, "points": []})

    def upsert(self, name: str, points: list[dict]):
        coll = self._store.setdefault(name, {"dim": 0, "points": []})
        index = {p["id"]: p for p in coll["points"]}
        for p in points:
            index[p["id"]] = p
        coll["points"] = list(index.values())

    def search(self, name: str, vector, top_k: int, kb_id=None) -> list[dict]:
        coll = self._store.get(name)
        if not coll:
            return []
        out = []
        for p in coll["points"]:
            if kb_id is not None and p["payload"].get("kb_id") != str(kb_id):
                continue
            out.append((_cosine(vector, p["vector"]), p))
        out.sort(key=lambda x: -x[0])
        results = []
        for score, p in out[:top_k]:
            results.append({
                "chunk_id": p["id"],
                "document_id": p["payload"]["document_id"],
                "score": score,
                "content": p["payload"]["content"],
                "meta": p["payload"].get("meta", {}),
            })
        return results

    def delete_document(self, name: str, document_id):
        coll = self._store.get(name)
        if not coll:
            return
        coll["points"] = [
            p for p in coll["points"]
            if p["payload"].get("document_id") != str(document_id)
        ]

    def count(self, name: str) -> int:
        return len(self._store.get(name, {}).get("points", []))


class QdrantVectorStore:
    def __init__(self, url: str | None = None, api_key: str | None = None, path: str | None = None):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        self._VectorParams = VectorParams
        self._Distance = Distance
        if path:
            # 嵌入式本地引擎：无需独立 Qdrant 服务端，向量落盘持久化（单机/边缘生产场景）
            self._client = QdrantClient(path=path)
        else:
            self._client = QdrantClient(url=url, api_key=api_key)

    def ensure_collection(self, name: str, dim: int):
        from qdrant_client.models import Distance, VectorParams
        if not self._client.collection_exists(name):
            self._client.create_collection(
                name, vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )

    def upsert(self, name: str, points: list[dict]):
        from qdrant_client.models import PointStruct
        self._client.upsert(name, points=[
            PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points
        ])

    def search(self, name: str, vector, top_k: int, kb_id=None) -> list[dict]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        qfilter = None
        if kb_id is not None:
            qfilter = Filter(must=[FieldCondition(key="kb_id", match=MatchValue(value=str(kb_id)))])
        hits = self._client.search(name, query_vector=vector, limit=top_k, query_filter=qfilter)
        return [{
            "chunk_id": str(h.id),
            "document_id": h.payload["document_id"],
            "score": float(h.score),
            "content": h.payload["content"],
            "meta": h.payload.get("meta", {}),
        } for h in hits]

    def delete_document(self, name: str, document_id):
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        self._client.delete(name, points_selector=Filter(must=[
            FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))
        ]))

    def count(self, name: str) -> int:
        try:
            return self._client.count(name).count
        except Exception:
            return 0


_STORE = None


def get_vector_store():
    global _STORE
    if _STORE is not None:
        return _STORE
    if QDRANT_URL:
        _STORE = QdrantVectorStore(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print(f"[vector_store] using Qdrant server @ {QDRANT_URL}")
    elif QDRANT_LOCAL_PATH:
        _STORE = QdrantVectorStore(path=QDRANT_LOCAL_PATH)
        print(f"[vector_store] using Qdrant local engine @ {QDRANT_LOCAL_PATH}")
    else:
        _STORE = InMemoryVectorStore()
        print("[vector_store] QDRANT_URL/QDRANT_LOCAL_PATH not set -> InMemory store (dev)")
    return _STORE
