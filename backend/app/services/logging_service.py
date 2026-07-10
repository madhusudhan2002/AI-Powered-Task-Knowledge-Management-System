from sqlalchemy.orm import Session
from app import models


def log_activity(db: Session, user_id: int | None, action: str, details: str = ""):
    entry = models.ActivityLog(user_id=user_id, action=action, details=details)
    db.add(entry)
    db.commit()
