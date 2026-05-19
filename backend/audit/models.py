import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.database import Base


# --- Enums ---

class AuditStatus(str, enum.Enum):
    SUCCESS = "success"     # action completed without error
    FAILURE = "failure"     # action was attempted but failed


# --- Model ---

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # who performed the action
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # what action was performed — e.g. "user.login", "document.upload", "department.delete"
    action = Column(String, nullable=False, index=True)

    # what type of resource was affected — e.g. "user", "document", "department"
    target_type = Column(String, nullable=True)

    # the ID of the affected resource — e.g. the document UUID that was deleted
    target_id = Column(String, nullable=True)

    # where the request came from
    ip_address = Column(String, nullable=True)

    # did it succeed or fail
    status = Column(Enum(AuditStatus), nullable=False, default=AuditStatus.SUCCESS)

    # any extra context — e.g. {"file_type": "pdf", "file_size": "2mb"}
    # stored as JSON so it's flexible — each action can store different metadata
    extra_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # relationships
    actor = relationship("User", foreign_keys=[actor_id])