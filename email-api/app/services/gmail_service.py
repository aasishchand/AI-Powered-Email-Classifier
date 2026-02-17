"""Gmail API integration using OAuth access tokens. Fetches and syncs emails."""
import asyncio
import base64
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SyncedEmail
from app.services.imap_service import _classify_simple, _strip_html_to_plain, _urgency_simple

logger = logging.getLogger(__name__)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
# Timeout per request so sync doesn't hang on slow Gmail responses
_HTTP_TIMEOUT = 30.0


async def list_messages(
    client: httpx.AsyncClient,
    access_token: str,
    max_results: int = 50,
    page_token: Optional[str] = None,
    q: Optional[str] = None,
) -> dict:
    """List message IDs from Gmail. Returns { messages: [{id, threadId}], nextPageToken? }."""
    params = {"maxResults": max_results}
    if page_token:
        params["pageToken"] = page_token
    if q:
        params["q"] = q
    r = await client.get(
        f"{GMAIL_API_BASE}/messages",
        params=params,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if r.status_code != 200:
        raise ValueError(f"Gmail list failed: {r.status_code} {r.text[:200]}")
    return r.json()


async def get_message(client: httpx.AsyncClient, access_token: str, msg_id: str) -> dict:
    """Get full message by ID (format=full)."""
    r = await client.get(
        f"{GMAIL_API_BASE}/messages/{msg_id}",
        params={"format": "full"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if r.status_code != 200:
        raise ValueError(f"Gmail get message failed: {r.status_code}")
    return r.json()


def _decode_b64(s: str) -> str:
    try:
        return base64.urlsafe_b64decode(s).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_payload(msg: dict) -> tuple[str, str]:
    """Extract subject, from, date, body from Gmail API message payload."""
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")
    from_ = headers.get("from", "")
    date_str = headers.get("date", "")
    try:
        received_at = parsedate_to_datetime(date_str) if date_str else datetime.utcnow()
    except Exception:
        received_at = datetime.utcnow()
    if received_at.tzinfo is None:
        from datetime import timezone
        received_at = received_at.replace(tzinfo=timezone.utc)

    body = ""
    payload = msg.get("payload", {})
    if payload.get("body", {}).get("data"):
        body = _decode_b64(payload["body"]["data"])
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            body = _decode_b64(part["body"]["data"])
            break
        if part.get("mimeType") == "text/html" and not body and part.get("body", {}).get("data"):
            body = _strip_html_to_plain(_decode_b64(part["body"]["data"]), max_len=50000)
    if body and len(body) > 50000:
        body = body[:50000]
    body_preview = (body or "")[:300].replace("\n", " ")
    sender_email = from_
    if "<" in from_ and ">" in from_:
        m = re.search(r"<([^>]+)>", from_)
        if m:
            sender_email = m.group(1).strip()
    sender_name = from_.replace(sender_email, "").strip(" <>\"'") or None
    return subject, from_, date_str, received_at, body, body_preview, sender_email, sender_name


def _parse_gmail_message(msg: dict) -> Optional[dict]:
    """Parse Gmail API message into our SyncedEmail row dict."""
    try:
        msg_id = msg.get("id")
        if not msg_id:
            return None
        payload = msg.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        subject, from_, _date_str, received_at, body, body_preview, sender_email, sender_name = _extract_payload(msg)
        spam_label, spam_score, topic, mailbox_type = _classify_simple(subject, body or "", sender_email)
        urgency_score = _urgency_simple(subject, body or "")
        message_id = f"gmail-{msg_id}"
        attachment_count = len([p for p in payload.get("parts", []) if p.get("filename")])
        return {
            "message_id": message_id,
            "sender": sender_email[:255],
            "sender_name": sender_name,
            "subject": subject[:1024],
            "body": body[:50000] if body else None,
            "body_preview": body_preview[:500] if body_preview else None,
            "received_at": received_at,
            "spam_label": spam_label,
            "spam_score": spam_score,
            "topic": topic,
            "mailbox_type": mailbox_type,
            "urgency_score": urgency_score,
            "attachment_count": attachment_count,
            "cc_count": len((headers.get("cc") or "").split(",")) if headers.get("cc") else 0,
        }
    except Exception:
        return None


# Max concurrent Gmail API get_message calls to avoid rate limits
_MAX_CONCURRENT_FETCH = 10


async def sync_emails_gmail(
    db: AsyncSession,
    user_id: str,
    access_token: str,
    max_emails: int = 50,
) -> int:
    """
    Fetch emails from Gmail API and save to SyncedEmail. Returns count of new emails saved.
    Uses a single shared httpx client and fetches messages concurrently (bounded).
    """
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        data = await list_messages(client, access_token, max_results=max_emails)
        messages = data.get("messages") or []
        if not messages:
            logger.info("Gmail sync for user %s: no messages returned", user_id)
            return 0

        logger.info("Gmail sync for user %s: fetching %d messages…", user_id, len(messages))
        sem = asyncio.Semaphore(_MAX_CONCURRENT_FETCH)

        async def fetch_one(m: dict):
            mid = m.get("id")
            if not mid:
                return None
            async with sem:
                try:
                    full = await get_message(client, access_token, mid)
                    return _parse_gmail_message(full)
                except Exception as e:
                    logger.warning("Failed to fetch Gmail message %s: %s", mid, e)
                    return None

        tasks = [fetch_one(m) for m in messages]
        rows = await asyncio.gather(*tasks)

    saved = 0
    for row in rows:
        if row is None:
            continue
        existing = await db.execute(
            select(SyncedEmail).where(SyncedEmail.user_id == user_id, SyncedEmail.message_id == row["message_id"])
        )
        if existing.scalar_one_or_none():
            continue
        rec = SyncedEmail(
            user_id=user_id,
            message_id=row["message_id"],
            sender=row["sender"],
            sender_name=row.get("sender_name"),
            subject=row["subject"],
            body=row.get("body"),
            body_preview=row.get("body_preview"),
            received_at=row["received_at"],
            spam_label=row.get("spam_label", "ham"),
            spam_score=row.get("spam_score", 0.0),
            topic=row.get("topic"),
            mailbox_type=row.get("mailbox_type"),
            urgency_score=row.get("urgency_score", 0.3),
            attachment_count=row.get("attachment_count", 0),
            cc_count=row.get("cc_count", 0),
        )
        db.add(rec)
        saved += 1
    await db.flush()
    logger.info("Gmail sync for user %s: saved %d new emails", user_id, saved)
    return saved


async def mark_as_read_gmail(access_token: str, msg_id: str) -> bool:
    """Remove UNREAD label from message (Gmail API). msg_id is Gmail message id."""
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.post(
                f"{GMAIL_API_BASE}/messages/{msg_id}/modify",
                json={"removeLabelIds": ["UNREAD"]},
                headers={"Authorization": f"Bearer {access_token}"},
            )
        return r.status_code == 200
    except Exception as e:
        logger.warning("mark_as_read_gmail failed for %s: %s", msg_id, e)
        return False
