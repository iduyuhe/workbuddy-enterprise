"""knowledge-service REST 路由，对齐 API_CONTRACT.md §3。"""
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import UPLOAD_ROOT
from app.core.db import get_db
from app.models.knowledge import Document, KnowledgeBase
from app.schemas.knowledge import (
    KnowledgeBaseCreate, KnowledgeBaseOut, DocumentStatus, SearchRequest, SearchResponse,
)
from app.services.rag import run_ingest, search

router = APIRouter()


def _to_kb_out(kb: KnowledgeBase) -> KnowledgeBaseOut:
    return KnowledgeBaseOut(
        id=kb.id, name=kb.name, project_id=kb.project_id,
        embedding=kb.embedding, collection=kb.collection,
        created_at=kb.created_at.isoformat() if kb.created_at else None,
    )


@router.post("/kb", response_model=KnowledgeBaseOut, status_code=201)
def create_kb(payload: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    collection = f"kb_{uuid.uuid4().hex[:12]}"
    kb = KnowledgeBase(
        name=payload.name, project_id=payload.project_id,
        embedding=payload.embedding, collection=collection,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)

    # 分配 Qdrant collection（若使用 Qdrant）；InMemory 在 ingest 时惰性建
    from app.services.embedder import get_embedder
    from app.services.vector_store import get_vector_store
    try:
        store = get_vector_store()
        store.ensure_collection(collection, get_embedder().dim)
    except Exception:
        # 不阻塞建库：向量库在 ingest 时再尝试
        pass
    return _to_kb_out(kb)


@router.get("/kb")
def list_kb(
    project_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
):
    stmt = select(KnowledgeBase)
    if project_id is not None:
        stmt = stmt.where(KnowledgeBase.project_id == project_id)
    rows = db.scalars(stmt.order_by(KnowledgeBase.created_at.desc())).all()
    return {"items": [_to_kb_out(k).model_dump() for k in rows], "total": len(rows)}


@router.get("/kb/{kb_id}", response_model=KnowledgeBaseOut)
def get_kb(kb_id: uuid.UUID, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    return _to_kb_out(kb)


@router.delete("/kb/{kb_id}")
def delete_kb(kb_id: uuid.UUID, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    # 级联删除文档与向量
    from app.services.vector_store import get_vector_store
    try:
        store = get_vector_store()
        if kb.collection:
            # 删除该 collection 下本 kb 所有 chunk（逐个文档清理）
            for doc in db.scalars(select(Document).where(Document.kb_id == kb_id)).all():
                store.delete_document(kb.collection, doc.id)
    except Exception:
        pass
    db.delete(kb)
    db.commit()
    return {"deleted": str(kb_id)}


@router.post("/kb/{kb_id}/ingest", status_code=202)
async def ingest(
    kb_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="knowledge base not found")

    document_id = uuid.uuid4()
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    save_path = os.path.join(UPLOAD_ROOT, f"{document_id.hex}{ext}")
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    doc = Document(
        id=document_id, kb_id=kb_id, title=file.filename,
        source_path=save_path, status="pending",
        meta_json={"content_type": file.content_type},
    )
    db.add(doc)
    db.commit()

    background_tasks.add_task(run_ingest, document_id, save_path)
    return {"document_id": str(document_id), "status": "parsing"}


@router.get("/kb/{kb_id}/documents", response_model=list[DocumentStatus])
def list_documents(kb_id: uuid.UUID, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    rows = db.scalars(select(Document).where(Document.kb_id == kb_id)).all()
    return [
        DocumentStatus(
            document_id=d.id, kb_id=d.kb_id, status=d.status,
            chunk_count=d.chunk_count, title=d.title,
        ) for d in rows
    ]


@router.get("/kb/{kb_id}/documents/{document_id}", response_model=DocumentStatus)
def get_document(kb_id: uuid.UUID, document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or doc.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="document not found")
    return DocumentStatus(
        document_id=doc.id, kb_id=doc.kb_id, status=doc.status,
        chunk_count=doc.chunk_count, title=doc.title,
    )


@router.delete("/kb/{kb_id}/documents/{document_id}")
def delete_document(kb_id: uuid.UUID, document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc or doc.kb_id != kb_id:
        raise HTTPException(status_code=404, detail="document not found")
    from app.services.vector_store import get_vector_store
    try:
        kb = db.get(KnowledgeBase, kb_id)
        if kb and kb.collection:
            get_vector_store().delete_document(kb.collection, document_id)
    except Exception:
        pass
    db.delete(doc)
    db.commit()
    return {"deleted": str(document_id)}


@router.post("/kb/{kb_id}/search", response_model=SearchResponse)
def search_kb(kb_id: uuid.UUID, payload: SearchRequest, db: Session = Depends(get_db)):
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    results = search(
        kb, payload.query, payload.top_k, payload.rerank, payload.score_threshold
    )
    return SearchResponse(results=results)
