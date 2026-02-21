"""Pydantic v2 schemas for Kafka and pipeline messages."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RawEmailMessage(BaseModel):
    """Kafka raw email message schema."""
    id: str = Field(..., description="Message/email ID")
    subject: str = Field("", description="Email subject")
    sender: str = Field("", description="Sender address")
    body_preview: str = Field("", description="Short body preview")
    received_at: str | None = Field(None, description="ISO timestamp")
    mailbox_type: str = Field("faculty", description="faculty | personal")
    raw_headers: str | None = Field(None, description="Raw headers string")

    model_config = {"extra": "allow"}


class ClassifiedEmailMessage(BaseModel):
    """Post-classification email schema."""
    id: str
    subject: str = ""
    sender: str = ""
    body_preview: str = ""
    received_at: str | None = None
    mailbox_type: str = "faculty"
    spam_label: str = "ham"
    spam_score: float = 0.0
    topic: str = "general"
    topic_confidence: float = 0.0
    urgency_score: float = 0.0
    sentiment_score: float = 0.0

    model_config = {"extra": "allow"}


class AnalyticsSummary(BaseModel):
    """Daily analytics output schema (MinIO JSON)."""
    metric_date: str
    daily_volume: int = 0
    spam_count: int = 0
    spam_rate: float = 0.0
    ham_count: int = 0
    topic_distribution: dict[str, int] = Field(default_factory=dict)
    avg_urgency_score: float = 0.0
    top_senders_by_domain: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str | None = None
