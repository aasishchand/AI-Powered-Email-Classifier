"""Database utilities for storing and updating classified emails."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Float,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    desc,
    func,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from project.utils.config import config

logger = logging.getLogger(__name__)

metadata = MetaData()

emails_table = Table(
    "emails",
    metadata,
    Column("email_id", String(36), primary_key=True),
    Column("text", Text, nullable=False),
    Column("predicted_label", String(50), nullable=False),
    Column("confidence", Float, nullable=True),
    Column("timestamp", TIMESTAMP, nullable=False, server_default=func.now()),
    Column("feedback", String(50), nullable=True, default=None),
    Column("feedback_at", TIMESTAMP, nullable=True, default=None),
    Column("pipeline_source", String(32), nullable=True),
)

engine: Engine = create_engine(
    config.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    echo=False,
    future=True,
)


def init_db() -> None:
    """Create tables if they don't exist. Call once at startup."""
    try:
        metadata.create_all(engine, checkfirst=True)
        if engine.dialect.name == "postgresql":
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE emails ADD COLUMN IF NOT EXISTS pipeline_source VARCHAR(32)")
                )
        logger.info("Database initialized successfully.")
    except SQLAlchemyError as exc:
        logger.exception("Failed to initialize database.")
        raise RuntimeError(f"Database initialization failed: {exc}") from exc


def insert_email(record: dict[str, Any]) -> None:
    """
    Insert a new classified email record.
    Expected keys: email_id, text, predicted_label, confidence, timestamp.
    """
    required = {"email_id", "text", "predicted_label", "confidence", "timestamp"}
    missing = required - set(record.keys())
    if missing:
        raise ValueError(f"insert_email missing required keys: {sorted(missing)}")

    payload = {
        "email_id": record["email_id"],
        "text": record["text"],
        "predicted_label": record["predicted_label"],
        "confidence": record["confidence"],
        "timestamp": record["timestamp"],
        "pipeline_source": record.get("pipeline_source"),
    }

    try:
        with engine.begin() as conn:
            conn.execute(emails_table.insert().values(**payload))
        logger.info("Inserted email record email_id=%s", payload["email_id"])
    except IntegrityError:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Failed to insert email record email_id=%s", payload["email_id"])
        raise RuntimeError(f"Failed to insert email record: {exc}") from exc


def update_feedback(email_id: str, correct_label: str) -> bool:
    """
    Update feedback and feedback_at for a given email_id.
    Returns True if a row was updated, False if email_id not found.
    """
    try:
        with engine.begin() as conn:
            stmt = (
                update(emails_table)
                .where(emails_table.c.email_id == email_id)
                .values(feedback=correct_label, feedback_at=datetime.utcnow())
            )
            result = conn.execute(stmt)
        updated = (result.rowcount or 0) > 0
        logger.info("Feedback update email_id=%s updated=%s", email_id, updated)
        return updated
    except SQLAlchemyError as exc:
        logger.exception("Failed to update feedback for email_id=%s", email_id)
        raise RuntimeError(f"Failed to update feedback: {exc}") from exc


def get_feedback_data() -> list[dict[str, Any]]:
    """Return all rows where feedback IS NOT NULL. Used by the retraining pipeline."""
    try:
        with engine.connect() as conn:
            stmt = select(
                emails_table.c.email_id,
                emails_table.c.text,
                emails_table.c.predicted_label,
                emails_table.c.confidence,
                emails_table.c.timestamp,
                emails_table.c.feedback,
                emails_table.c.feedback_at,
            ).where(emails_table.c.feedback.is_not(None))
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]
    except SQLAlchemyError as exc:
        logger.exception("Failed to fetch feedback data.")
        raise RuntimeError(f"Failed to fetch feedback data: {exc}") from exc


def get_recent_emails(limit: int = 20, pipeline_source: Optional[str] = None) -> list[dict[str, Any]]:
    """Return the most recent classified emails for dashboard/list APIs.

    When ``pipeline_source`` is set (e.g. ``mailbox``, ``synthetic``, ``demo``),
    only matching rows are returned.
    """
    safe_limit = max(1, min(limit, 500))
    try:
        with engine.connect() as conn:
            stmt = select(
                emails_table.c.email_id,
                emails_table.c.text,
                emails_table.c.predicted_label,
                emails_table.c.confidence,
                emails_table.c.timestamp,
                emails_table.c.feedback,
                emails_table.c.feedback_at,
                emails_table.c.pipeline_source,
            ).order_by(desc(emails_table.c.timestamp))
            if pipeline_source:
                stmt = stmt.where(emails_table.c.pipeline_source == pipeline_source)
            stmt = stmt.limit(safe_limit)
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]
    except SQLAlchemyError as exc:
        logger.exception("Failed to fetch recent emails.")
        raise RuntimeError(f"Failed to fetch recent emails: {exc}") from exc
