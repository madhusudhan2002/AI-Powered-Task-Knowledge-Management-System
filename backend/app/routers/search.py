from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.deps import get_current_user
from app.services.vector_store import search as vector_search
from app.services.logging_service import log_activity
router = APIRouter(prefix="/search", tags=["Search"])
@router.get("", response_model=schemas.SearchResponse)
def semantic_search(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    AI-powered semantic search:
    query -> embedding -> FAISS similarity search -> map back to source chunks.
    """
    raw_results = vector_search(q, top_k=top_k)
    results = []
    for vector_index, score in raw_results:
        chunk = (
            db.query(models.DocumentChunk)
            .filter(models.DocumentChunk.vector_index == vector_index)
            .first()
        )
        if not chunk:
            continue
        document = db.query(models.Document).filter(
            models.Document.id == chunk.document_id
        ).first()
        results.append(schemas.SearchResultItem(
            document_id=chunk.document_id,
            filename=document.filename if document else "unknown",
            chunk_text=chunk.chunk_text,
            score=round(score, 4),
        ))
    db.add(models.SearchQuery(
        user_id=current_user.id, query_text=q, result_count=len(results)
    ))
    log_activity(db, user_id=current_user.id, action="search", details=f"query='{q}'")
    db.commit()
    return schemas.SearchResponse(query=q, results=results)