"""知识库 Pydantic schemas（本地定义，对齐 API_CONTRACT.md §3）。"""
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str
    project_id: Optional[UUID] = None
    tenant_id: Optional[str] = None
    embedding: str = "bge-m3"


class KnowledgeBaseOut(BaseModel):
    id: UUID
    name: str
    project_id: Optional[UUID] = None
    tenant_id: Optional[str] = None
    embedding: str
    collection: Optional[str] = None
    created_at: Optional[str] = None


class DocumentStatus(BaseModel):
    document_id: UUID
    kb_id: UUID
    status: str
    chunk_count: int
    title: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    rerank: bool = True
    score_threshold: Optional[float] = 0.3


class SearchResult(BaseModel):
    chunk_id: str
    document_id: UUID
    score: float
    content: str
    meta: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: list[SearchResult]
