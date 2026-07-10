from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.models import RoleName, TaskStatus
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleName = RoleName.user
class UserLogin(BaseModel):
    email: EmailStr
    password: str
class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    class Config:
        from_attributes = True
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: Optional[int] = None
class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[int] = None
class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    assigned_to: Optional[int]
    created_by: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    uploaded_by: int
    uploaded_at: datetime
    is_indexed: bool
    chunk_count: int
    class Config:
        from_attributes = True
class SearchResultItem(BaseModel):
    document_id: int
    filename: str
    chunk_text: str
    score: float
class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
class TopQuery(BaseModel):
    query_text: str
    count: int
class AnalyticsOut(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    total_documents: int
    total_users: int
    top_search_queries: List[TopQuery]