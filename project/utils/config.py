"""Centralized configuration for the email pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Runtime configuration loaded from environment variables."""

    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC: str = os.getenv("KAFKA_TOPIC", "email-stream")
    # latest: only new messages after consumer starts (typical real-time). Use "earliest" to replay the topic.
    KAFKA_AUTO_OFFSET_RESET: str = os.getenv("KAFKA_AUTO_OFFSET_RESET", "latest")

    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "email_pipeline")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")

    MODEL_PATH: str = os.getenv("MODEL_PATH", "model/model.pkl")
    VECTORIZER_PATH: str = os.getenv("VECTORIZER_PATH", "model/vectorizer.pkl")

    FEEDBACK_API_PORT: int = int(os.getenv("FEEDBACK_API_PORT", "5000"))

    @property
    def DATABASE_URL(self) -> str:
        """Assemble SQLAlchemy PostgreSQL URL."""
        return (
            "postgresql://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


config = Config()
