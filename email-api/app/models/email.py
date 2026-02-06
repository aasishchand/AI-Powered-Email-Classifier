"""Pydantic models for email entities."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Email(BaseModel):
    message_id: str
    sender: str
    sender_name: Optional[str] = None
    subject: str
    body: Optional[str] = None
    body_preview: Optional[str] = None
    timestamp: str
    spam_label: str
    spam_score: float
    topic: Optional[str] = None
    topic_confidence: Optional[float] = None
    urgency_score: float = 0.0
    sentiment_score: float = 0.0
    attachment_count: int = 0
    cc_count: int = 0
    mailbox_type: Optional[str] = None  # "faculty" | "personal"


class EmailFilters(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    topic: Optional[str] = None
    spam_label: Optional[str] = None
    sender: Optional[str] = None
    search: Optional[str] = None
    mailbox_type: Optional[str] = None  # "faculty" | "personal"


class EmailReclassifyRequest(BaseModel):
    label: str = Field(..., pattern="^(spam|ham)$")
    reason: Optional[str] = None
