import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.deps import require_admin, get_current_user
from app.config import settings
from app.services.file_parser import extract_text, chunk_text
from app.services.vector_store import add_chunks
from app.services.logging_service import log_activity
router = APIRouter(prefix="/documents", tags=["Documents"])
ALLOWED_EXTENSIONS = {"txt", "pdf"}
@router.post("/upload", response_model=schemas.DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .txt and .pdf files are allowed")
    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    document = models.Document(
        filename=file.filename,
        filepath=filepath,
        file_type=ext,
        uploaded_by=admin.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    try:
        raw_text = extract_text(filepath, ext)
        chunks = chunk_text(raw_text)
        vector_ids = add_chunks(chunks)
        for chunk, vec_id in zip(chunks, vector_ids):
            db.add(models.DocumentChunk(
                document_id=document.id,
                chunk_text=chunk,
                vector_index=vec_id,
            ))
        document.is_indexed = True
        document.chunk_count = len(chunks)
        db.commit()
        db.refresh(document)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")
    log_activity(
        db, user_id=admin.id, action="document_upload",
        details=f"uploaded '{file.filename}' ({document.chunk_count} chunks indexed)"
    )
    return document
@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Document).order_by(models.Document.uploaded_at.desc()).all()