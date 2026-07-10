from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.deps import get_current_user, require_admin
from app.services.logging_service import log_activity
router = APIRouter(prefix="/tasks", tags=["Tasks"])
@router.post("", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    task = models.Task(
        title=payload.title,
        description=payload.description,
        assigned_to=payload.assigned_to,
        created_by=admin.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
@router.get("", response_model=list[schemas.TaskOut])
def list_tasks(
    status_filter: Optional[models.TaskStatus] = None,
    assigned_to: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Dynamic filtering API: /tasks?status_filter=completed&assigned_to=1
    Admins see all tasks; regular users only see tasks assigned to them.
    """
    query = db.query(models.Task)
    if current_user.role.name == models.RoleName.user:
        query = query.filter(models.Task.assigned_to == current_user.id)
    elif assigned_to is not None:
        query = query.filter(models.Task.assigned_to == assigned_to)
    if status_filter is not None:
        query = query.filter(models.Task.status == status_filter)
    return query.order_by(models.Task.created_at.desc()).all()
@router.patch("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    is_admin = current_user.role.name == models.RoleName.admin
    is_owner = task.assigned_to == current_user.id
    if not is_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Not authorized to update this task")
    if not is_admin and payload.status is None:
        raise HTTPException(status_code=403, detail="Users may only update task status")
    if payload.status is not None:
        task.status = payload.status
    if is_admin:
        if payload.title is not None:
            task.title = payload.title
        if payload.description is not None:
            task.description = payload.description
        if payload.assigned_to is not None:
            task.assigned_to = payload.assigned_to
    db.commit()
    db.refresh(task)
    log_activity(
        db,
        user_id=current_user.id,
        action="task_update",
        details=f"task {task_id} updated -> status={task.status.value}",
    )
    return task
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()