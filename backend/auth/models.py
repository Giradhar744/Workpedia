import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime,
    Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.database import Base


# --- Enums ---

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    DEPT_ADMIN = "dept_admin"
    EMPLOYEE = "employee"


class OTPPurpose(str, enum.Enum):
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"


# --- Models ---

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    is_active = Column(Boolean, default=True)
    is_suspended = Column(Boolean, default=False)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    department = relationship("Department", foreign_keys=[department_id])
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    otp_codes = relationship("OTPCode", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String, nullable=False, unique=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    user = relationship("User", back_populates="sessions")


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String, nullable=False)
    purpose = Column(Enum(OTPPurpose), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    user = relationship("User", back_populates="otp_codes")