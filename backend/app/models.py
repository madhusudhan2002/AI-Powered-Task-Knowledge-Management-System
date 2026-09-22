import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


# ==================================================
# Role Enum
# ==================================================

class RoleName(str, enum.Enum):
    admin = "admin"
    user = "user"


# ==================================================
# Task Status Enum
# ==================================================

class TaskStatus(str, enum.Enum):

    pending = "pending"
    completed = "completed"


# ==================================================
# Role Model
# ==================================================

class Role(Base):
    __tablename__ = "roles"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        Enum(RoleName),
        unique=True,
        nullable=False
    )

    users = relationship(
        "User",
        back_populates="role"
    )


# ==================================================
# User Model
# ==================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(150),
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )

    hashed_password = Column(
        String(255),
        nullable=False
    )

    role_id = Column(
        Integer,
        ForeignKey("roles.id"),
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    role = relationship(
        "Role",
        back_populates="users"
    )

    documents = relationship(
        "Document",
        back_populates="uploaded_by_user"
    )

    assigned_tasks = relationship(
        "Task",
        back_populates="assigned_to_user",
        foreign_keys="Task.assigned_to"
    )

    created_tasks = relationship(
        "Task",
        back_populates="created_by_user",
        foreign_keys="Task.created_by"
    )

    activity_logs = relationship(
        "ActivityLog",
        back_populates="user"
    )

    search_queries = relationship(
        "SearchQuery",
        back_populates="user"
    )


# ==================================================
# Document Model
# ==================================================

class Document(Base):
    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    filename = Column(
        String(255),
        nullable=False
    )

    filepath = Column(
        String(500),
        nullable=False
    )

    file_type = Column(
        String(20),
        nullable=False
    )

    # SHA-256 hash used to detect duplicate files
    file_hash = Column(
        String(64),
        nullable=True,
        index=True
    )

    uploaded_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    is_indexed = Column(
        Boolean,
        default=False
    )

    chunk_count = Column(
        Integer,
        default=0
    )

    uploaded_by_user = relationship(
        "User",
        back_populates="documents"
    )

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )


# ==================================================
# Document Chunk Model
# ==================================================

class DocumentChunk(Base):
    """
    Maps FAISS vector index positions
    back to source text for retrieval.
    """

    __tablename__ = "document_chunks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=False
    )

    chunk_text = Column(
        Text,
        nullable=False
    )

    vector_index = Column(
        Integer,
        nullable=False,
        unique=True
    )

    document = relationship(
        "Document",
        back_populates="chunks"
    )


# ==================================================
# Task Model
# ==================================================

class Task(Base):
    __tablename__ = "tasks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(
        String(255),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    status = Column(
        Enum(TaskStatus),
        default=TaskStatus.pending,
        nullable=False
    )

    assigned_to = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    assigned_to_user = relationship(
        "User",
        back_populates="assigned_tasks",
        foreign_keys=[assigned_to]
    )

    created_by_user = relationship(
        "User",
        back_populates="created_tasks",
        foreign_keys=[created_by]
    )


# ==================================================
# Activity Log Model
# ==================================================

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    action = Column(
        String(100),
        nullable=False
    )

    details = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="activity_logs"
    )


# ==================================================
# Search Query Model
# ==================================================

class SearchQuery(Base):
    """
    Stores every search query for analytics.
    """

    __tablename__ = "search_queries"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    query_text = Column(
        String(500),
        nullable=False
    )

    result_count = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="search_queries"
    )