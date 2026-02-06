"""Pydantic models for dashboard and analytics."""
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class TopicInfo(BaseModel):
    name: str
    category: str
    count: int


class DashboardMetrics(BaseModel):
    total_emails: int = Field(..., description="Total number of emails")
    spam_count: int = Field(..., description="Number of spam emails detected")
    spam_percentage: float = Field(..., description="Percentage of spam emails")
    avg_sentiment: float = Field(..., description="Average sentiment score (-1 to 1)")
    avg_urgency: float = Field(..., description="Average urgency score (0 to 1)")
    top_topics: List[TopicInfo] = Field(default_factory=list, description="Top email topics")
    time_saved_hours: float = Field(..., description="Estimated time saved by classification")
    avg_response_time: float = Field(..., description="Average response time in hours")
    change_from_yesterday: float = Field(..., description="Percentage change from yesterday")
    avg_email_length: int = Field(..., description="Average email body length")


class EmailTrend(BaseModel):
    date: date
    total: int
    spam: int
    ham: int
    urgent: int


class TopicTrend(BaseModel):
    topic: str
    category: str
    weekly_count: int
    change_percentage: float
