import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from core.database import Base


# --- Enums ---

class MessageRole(str, enum.Enum):
    USER = "user"               # the employee's question
    ASSISTANT = "assistant"     # Claude's answer


# --- Models ---

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # which user started this chat session
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # which department context this session belongs to
    # determines which documents Claude can pull from
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    user = relationship("User", foreign_keys=[user_id])
    department = relationship("Department", foreign_keys=[department_id])
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # which session this message belongs to
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)

    # user = employee's question | assistant = Claude's answer
    role = Column(Enum(MessageRole), nullable=False)

    # the actual text content of the message
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    session = relationship("ChatSession", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", uselist=False, cascade="all, delete-orphan")
    # uselist=False → one message has at most one feedback (one-to-one)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # which assistant message was rated — only assistant messages get feedback
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)

    # who gave the feedback
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # rating from 1 (terrible) to 5 (excellent)
    rating = Column(Integer, nullable=False)

    # optional written comment
    comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    message = relationship("ChatMessage", back_populates="feedback")
    user = relationship("User", foreign_keys=[user_id])