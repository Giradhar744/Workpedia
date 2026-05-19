import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.database import Base


# --- Enums ---

class AccessLevel(str, enum.Enum):
    DEPARTMENT = "department"   # only visible to users in this department
    GLOBAL = "global"           # visible to all users across all departments


class IngestionStatus(str, enum.Enum):
    PENDING = "pending"         # job created, not yet picked up by worker
    PROCESSING = "processing"   # worker is actively processing the document
    COMPLETED = "completed"     # document fully parsed, chunked, embedded, stored
    FAILED = "failed"           # something went wrong — error_message will say what


# --- Models ---

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)                           # original file name
    file_type = Column(String, nullable=False)                      # pdf, docx, pptx etc.
    cloudinary_url = Column(String, nullable=False)                 # where the raw file lives
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    access_level = Column(Enum(AccessLevel), nullable=False, default=AccessLevel.DEPARTMENT)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    department = relationship("Department", foreign_keys=[department_id])
    uploader = relationship("User", foreign_keys=[uploaded_by])
    ingestion_jobs = relationship("IngestionJob", back_populates="document", cascade="all, delete-orphan")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(IngestionStatus), nullable=False, default=IngestionStatus.PENDING)
    error_message = Column(Text, nullable=True)     # filled only when status = FAILED
    started_at = Column(DateTime, nullable=True)    # when Celery worker picked it up
    completed_at = Column(DateTime, nullable=True)  # when processing finished
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    document = relationship("Document", back_populates="ingestion_jobs")