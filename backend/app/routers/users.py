from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.deps import require_admin
router = APIRouter(prefix="/users", tags=["Users"])
@router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    users = db.query(models.User).all()
    return [
        schemas.UserOut(id=u.id, name=u.name, email=u.email, role=u.role.name.value)
        for u in users
    ]