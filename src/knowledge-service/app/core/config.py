"""knowledge-service 配置（env 驱动）。"""
import os

SERVICE_NAME = "knowledge-service"
PORT = int(os.getenv("PORT", "8005"))

HEADER_USER_ID = "X-User-Id"
HEADER_PROJECT_ID = "X-Project-Id"

# Qdrant：未配置则使用进程内 InMemory 向量库（dev / 单机演示）
QDRANT_URL = os.getenv("QDRANT_URL")  # e.g. http://localhost:6333
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Embedding 模型名（sentence-transformers / FlagEmbedding）
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# 切片参数
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ingest 临时落盘目录
UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", "./kb_uploads")
os.makedirs(UPLOAD_ROOT, exist_ok=True)
