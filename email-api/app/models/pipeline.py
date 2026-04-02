"""Pydantic models for Kafka + sklearn pipeline (PostgreSQL)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PipelineEmailItem(BaseModel):
    email_id: str
    text: str
    predicted_label: str
    confidence: Optional[float] = None
    timestamp: Optional[str] = None
    feedback: Optional[str] = None
    feedback_at: Optional[str] = None
    pipeline_source: Optional[str] = None


class PipelineEmailsResponse(BaseModel):
    items: list[PipelineEmailItem]
    count: int


class PipelineFeedbackRequest(BaseModel):
    email_id: str = Field(..., min_length=1)
    correct_label: str = Field(..., min_length=1)


class PipelineFeedbackResponse(BaseModel):
    status: str
    email_id: str


class PipelinePublishResponse(BaseModel):
    status: str
    email_id: str
    topic: str


class PipelineMailboxPublishResponse(BaseModel):
    published: int
    topic: str
    source: str
