from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.deps import get_current_user
router = APIRouter(prefix="/analytics", tags=["Analytics"])
@router.get("", response_model=schemas.AnalyticsOut)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tasks = db.query(models.Task).all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == models.TaskStatus.completed)
    pending_tasks = total_tasks - completed_tasks
    total_documents = db.query(models.Document).count()
    total_users = db.query(models.User).count()
    query_rows = db.query(models.SearchQuery.query_text).all()
    counts = Counter(q[0].strip().lower() for q in query_rows)
    top_queries = [
        schemas.TopQuery(query_text=text, count=count)
        for text, count in counts.most_common(10)
    ]
    return schemas.AnalyticsOut(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        total_documents=total_documents,
        total_users=total_users,
        top_search_queries=top_queries,
    )