"""Embedding 封装：优先 bge-m3（sentence-transformers），加载失败降级为哈希向量（仅演示）。

- 生产：BAAI/bge-m3，输出维度 1024，normalize_embeddings=True。
- 降级：基于词哈希的稠密向量（低质量，仅供本地无 GPU / 无模型时跑通链路）。
"""
import hashlib
import os
import re

import numpy as np

from app.core.config import EMBEDDING_MODEL

_EMBEDDER = None


class BgeM3Embedder:
    dim = 1024

    def __init__(self, model):
        self.model = model

    def encode(self, texts: list[str]) -> list[list[float]]:
        embs = self.model.encode(texts, normalize_embeddings=True)
        return np.asarray(embs, dtype=np.float32).tolist()


class FallbackEmbedder:
    dim = 256

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in re.findall(r"\w+", text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


def get_embedder():
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDING_MODEL)
        _EMBEDDER = BgeM3Embedder(model)
        print(f"[embedder] loaded {EMBEDDING_MODEL} (dim={_EMBEDDER.dim})")
    except Exception as e:  # noqa: BLE001
        print(
            f"[embedder] WARNING: failed to load {EMBEDDING_MODEL} ({e}); "
            f"using fallback hash embedder (low quality, MVP-only)"
        )
        _EMBEDDER = FallbackEmbedder()
    return _EMBEDDER
