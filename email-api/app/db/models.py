"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="faculty", nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    original_label: Mapped[str] = mapped_column(String(50), nullable=False)
    corrected_label: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UserMailbox(Base):
    """Stores connected mailbox (IMAP) per user - one active per user."""
    __tablename__ = "user_mailboxes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mailbox_email: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    imap_server: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_port: Mapped[int] = mapped_column(nullable=False, default=993)
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SyncedEmail(Base):
    """Emails fetched from user's mailbox and classified."""
    __tablename__ = "synced_emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(1024), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_preview: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    spam_label: Mapped[str] = mapped_column(String(20), nullable=False, default="ham")
    spam_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    topic_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    urgency_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    attachment_count: Mapped[int] = mapped_column(nullable=False, default=0)
    cc_count: Mapped[int] = mapped_column(nullable=False, default=0)
    mailbox_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
