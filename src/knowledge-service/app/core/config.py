"""knowledge-service 配置（env 驱动）。"""
import os

SERVICE_NAME = "knowledge-service"
PORT = int(os.getenv("PORT", "8005"))

HEADER_USER_ID = "X-User-Id"
HEADER_PROJECT_ID = "X-Project-Id"

# Qdrant：优先级 QDRANT_URL(独立服务端) > QDRANT_LOCAL_PATH(嵌入式本地引擎) > InMemory(dev 默认)
QDRANT_URL = os.getenv("QDRANT_URL")  # e.g. http://localhost:6333
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH")  # 嵌入式本地引擎（免服务端），如 ./.qdrant_storage

# Embedding 模型名（sentence-transformers / FlagEmbedding）
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# 切片参数
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ingest 临时落盘目录
UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", "./kb_uploads")
os.makedirs(UPLOAD_ROOT, exist_ok=True)
