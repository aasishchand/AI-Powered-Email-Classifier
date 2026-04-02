"""Unified API: Kafka/sklearn pipeline data (same PostgreSQL as project.consumer)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional
import uuid

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import SyncedEmail
from app.db.session import get_db
from app.models.pipeline import (
    PipelineEmailItem,
    PipelineEmailsResponse,
    PipelineFeedbackRequest,
    PipelineFeedbackResponse,
    PipelineMailboxPublishResponse,
    PipelinePublishResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_pipeline_db_mod = None
_repo_env_loaded = False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _ensure_repo_env() -> None:
    """Load repo-root ``.env`` (Kafka + Postgres for pipeline) when API runs from ``email-api/``."""
    global _repo_env_loaded
    if _repo_env_loaded:
        return
    load_dotenv(_repo_root() / ".env")
    _repo_env_loaded = True


def _get_pipeline_db():
    """Lazy import of ``project.database.db``; repo root must be on ``sys.path``."""
    global _pipeline_db_mod
    if _pipeline_db_mod is not None:
        return _pipeline_db_mod

    repo_root = Path(__file__).resolve().parents[5]
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    load_dotenv(repo_root / ".env")

    try:
        from project.database import db as pipeline_db
    except ImportError as exc:
        logger.exception("Pipeline package not importable. Is the repo root correct?")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline module not available on server path.",
        ) from exc

    _pipeline_db_mod = pipeline_db
    return pipeline_db


def _serialize_cell(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return val


def _serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append({k: _serialize_cell(v) for k, v in row.items()})
    return out


def _stable_pipeline_id(message_id: str) -> str:
    """UUID v5 fits ``emails.email_id`` VARCHAR(36); stable per mailbox message id."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mailbox:{message_id}"))


def _compose_mail_text(subject: str, sender: str, body: str | None, preview: str | None) -> str:
    main = (body or preview or "").strip()
    return f"Subject: {subject}\nFrom: {sender}\n\n{main}"[:120000]


def _publish_events_sync(events: list[dict[str, Any]]) -> str:
    """Send events to Kafka; return topic name."""
    if not events:
        raise ValueError("no Kafka events to publish")
    _ensure_repo_env()
    try:
        from kafka import KafkaProducer
    except ImportError as exc:
        raise RuntimeError("kafka-python is not installed on the API server") from exc

    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.environ.get("KAFKA_TOPIC", "email-stream")
    producer = KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=3,
        request_timeout_ms=30000,
    )
    try:
        for ev in events:
            producer.send(topic, ev)
        producer.flush(timeout=90)
    finally:
        producer.close()
    return topic


_MAX_GMAIL_FETCH = 10


async def _events_from_synced_db(db: AsyncSession, user_id: str, max_emails: int) -> list[dict[str, Any]]:
    r = await db.execute(
        select(SyncedEmail)
        .where(SyncedEmail.user_id == user_id)
        .order_by(SyncedEmail.received_at.desc())
        .limit(max_emails)
    )
    rows = r.scalars().all()
    events: list[dict[str, Any]] = []
    for se in rows:
        ts = se.received_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        events.append(
            {
                "email_id": _stable_pipeline_id(se.message_id),
                "text": _compose_mail_text(se.subject, se.sender, se.body, se.body_preview),
                "timestamp": ts.isoformat(),
                "pipeline_source": "mailbox",
            }
        )
    return events


async def _events_from_gmail_live(db: AsyncSession, user_id: str, max_emails: int) -> list[dict[str, Any]]:
    from app.services.gmail_service import _parse_gmail_message, get_message, list_messages
    from app.services.token_manager import get_valid_access_token

    token = await get_valid_access_token(db, user_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Google account linked. Sign in with Gmail or use source=synced after syncing your inbox.",
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = await list_messages(client, token, max_results=max_emails)
        messages = data.get("messages") or []
        if not messages:
            return []
        sem = asyncio.Semaphore(_MAX_GMAIL_FETCH)

        async def fetch_one(m: dict):
            mid = m.get("id")
            if not mid:
                return None
            async with sem:
                try:
                    full = await get_message(client, token, mid)
                    return _parse_gmail_message(full)
                except Exception as e:
                    logger.warning("Gmail fetch failed for %s: %s", mid, e)
                    return None

        parsed = await asyncio.gather(*[fetch_one(m) for m in messages])

    events: list[dict[str, Any]] = []
    for row in parsed:
        if not row:
            continue
        ts = row["received_at"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        events.append(
            {
                "email_id": _stable_pipeline_id(row["message_id"]),
                "text": _compose_mail_text(row["subject"], row["sender"], row.get("body"), row.get("body_preview")),
                "timestamp": ts.isoformat(),
                "pipeline_source": "mailbox",
            }
        )
    return events


@router.get("/emails", response_model=PipelineEmailsResponse)
async def list_pipeline_emails(
    limit: int = Query(50, ge=1, le=200),
    pipeline_source: Optional[str] = Query(
        None,
        description="Filter by origin: mailbox | synthetic | demo | unknown",
    ),
    current_user: dict = Depends(get_current_user),
):
    """Recent classified emails from the real-time Kafka → sklearn → Postgres pipeline."""
    del current_user  # auth only

    def fetch():
        pdb = _get_pipeline_db()
        rows = pdb.get_recent_emails(limit=limit, pipeline_source=pipeline_source)
        return _serialize_rows(rows)

    try:
        raw = await asyncio.to_thread(fetch)
    except Exception as exc:
        logger.exception("Pipeline DB read failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Pipeline database unavailable: {exc}",
        ) from exc

    items = [PipelineEmailItem.model_validate(r) for r in raw]
    return PipelineEmailsResponse(items=items, count=len(items))


@router.post("/feedback", response_model=PipelineFeedbackResponse)
async def post_pipeline_feedback(
    body: PipelineFeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    """Correct a pipeline classification (feeds adaptive retraining)."""
    del current_user

    def do_update():
        pdb = _get_pipeline_db()
        return pdb.update_feedback(body.email_id, body.correct_label)

    try:
        ok = await asyncio.to_thread(do_update)
    except Exception as exc:
        logger.exception("Pipeline feedback failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Pipeline database unavailable: {exc}",
        ) from exc

    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="email_id not found")
    return PipelineFeedbackResponse(status="updated", email_id=body.email_id)


def _publish_one_to_kafka_sync() -> tuple[str, str]:
    """Return (email_id, topic). Raises on broker errors."""
    text = (
        "UI sample: Team meeting invite for sprint planning tomorrow at 10:00. "
        "Please review the attached agenda."
    )
    email_id = str(uuid.uuid4())
    payload = {
        "email_id": email_id,
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_source": "demo",
    }
    topic = _publish_events_sync([payload])
    return email_id, topic


@router.post("/publish-sample", response_model=PipelinePublishResponse)
async def publish_sample_to_kafka(current_user: dict = Depends(get_current_user)):
    """Send one synthetic email event to Kafka (same shape as ``email_producer``). Requires broker up."""
    del current_user
    try:
        email_id, topic = await asyncio.to_thread(_publish_one_to_kafka_sync)
    except Exception as exc:
        logger.exception("Kafka publish failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not publish to Kafka (is the broker running at KAFKA_BOOTSTRAP_SERVERS?): {exc}",
        ) from exc
    return PipelinePublishResponse(status="sent", email_id=email_id, topic=topic)


@router.post("/publish-mailbox", response_model=PipelineMailboxPublishResponse)
async def publish_mailbox_to_kafka(
    max_emails: int = Query(25, ge=1, le=100),
    source: str = Query(
        "gmail",
        description="'gmail' = fetch live from Gmail API; 'synced' = use emails already saved in the app DB",
    ),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Publish real mailbox messages to Kafka for the sklearn consumer.

    - **gmail**: requires Google sign-in with Gmail scopes; fetches latest messages from Gmail.
    - **synced**: uses rows in ``synced_emails`` (from Gmail or IMAP sync) — sync mail in **Emails** first.
    """
    src = (source or "gmail").lower().strip()
    if src not in ("gmail", "synced"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source must be 'gmail' or 'synced'",
        )
    user_id = current_user["id"]
    if src == "synced":
        events = await _events_from_synced_db(db, user_id, max_emails)
    else:
        events = await _events_from_gmail_live(db, user_id, max_emails)

    if not events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No emails to publish. For synced: run inbox sync on the Emails page first. For gmail: link Google or check inbox is not empty.",
        )
    try:
        topic = await asyncio.to_thread(_publish_events_sync, events)
    except Exception as exc:
        logger.exception("Kafka mailbox publish failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return PipelineMailboxPublishResponse(published=len(events), topic=topic, source=src)
