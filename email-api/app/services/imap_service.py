"""Real-time email ingestion via IMAP (e.g. Gmail with App Password)."""
import email
import imaplib
import re
from datetime import datetime
from email.header import decode_header
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_password
from app.db.models import SyncedEmail, UserMailbox


# Default IMAP servers
IMAP_SERVERS = {
    "gmail.com": ("imap.gmail.com", 993),
    "outlook.com": ("outlook.office365.com", 993),
    "yahoo.com": ("imap.mail.yahoo.com", 993),
    "hotmail.com": ("outlook.office365.com", 993),
}


def _get_imap_server(mailbox_email: str) -> Tuple[str, int]:
    domain = mailbox_email.split("@")[-1].lower() if "@" in mailbox_email else ""
    return IMAP_SERVERS.get(domain, ("imap.gmail.com", 993))


def _decode_mime_header(s: Optional[str]) -> str:
    if not s:
        return ""
    decoded = decode_header(s)
    out = []
    for part, enc in decoded:
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(part or "")
    return " ".join(out)


def _extract_body(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(errors="replace")
                    break
                except Exception:
                    pass
            elif ct == "text/html" and not body:
                try:
                    body = part.get_payload(decode=True).decode(errors="replace")
                    body = re.sub(r"<[^>]+>", " ", body)[:2000]
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True)
            if body:
                body = body.decode(errors="replace")
        except Exception:
            body = str(msg.get_payload())[:2000]
    return (body or "")[:5000]


def _classify_simple(subject: str, body: str, sender: str) -> Tuple[str, float, str, str]:
    """Simple rule-based classification (spam/topic/mailbox_type). Replace with ML later."""
    text = (subject + " " + body + " " + sender).lower()
    spam_score = 0.1
    if any(x in text for x in ["winner", "congratulations", "claim now", "click here", "unsubscribe", "viagra", "lottery"]):
        spam_score = 0.9
    spam_label = "spam" if spam_score > 0.6 else "ham"
    # Topic heuristics
    if "meeting" in text or "agenda" in text or "syllabus" in text or "course" in text:
        topic = "Academic - Course Materials"
    elif "grant" in text or "research" in text or "paper" in text:
        topic = "Research - Grant Opportunities"
    elif "event" in text or "invitation" in text or "seminar" in text:
        topic = "Events - Seminars & Conferences"
    elif "order" in text or "shipping" in text or "amazon" in text:
        topic = "Shopping"
    elif "newsletter" in text or "subscribe" in text:
        topic = "Newsletter"
    else:
        topic = "General Announcements"
    # Personal vs faculty by sender domain
    personal_domains = ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "live.com", "icloud.com")
    domain = sender.split("@")[-1].lower() if "@" in sender else ""
    mailbox_type = "personal" if any(d in domain for d in personal_domains) else "faculty"
    return spam_label, spam_score, topic, mailbox_type


def fetch_emails_imap(
    mailbox_email: str,
    password: str,
    imap_server: Optional[str] = None,
    imap_port: int = 993,
    max_emails: int = 50,
) -> List[dict]:
    """Connect via IMAP and fetch recent emails. Returns list of dicts for SyncedEmail."""
    server, port = _get_imap_server(mailbox_email) if not imap_server else (imap_server, imap_port)
    results = []
    try:
        if port == 993:
            M = imaplib.IMAP4_SSL(server, port=port)
        else:
            M = imaplib.IMAP4(server, port=port)
        M.login(mailbox_email, password)
        M.select("INBOX")
        typ, data = M.search(None, "ALL")
        if typ != "OK":
            return results
        ids = data[0].split()
        if not ids:
            M.logout()
            return results
        # Fetch most recent first
        ids = ids[-max_emails:] if len(ids) > max_emails else ids
        ids.reverse()
        for eid in ids:
            try:
                typ, msg_data = M.fetch(eid, "(RFC822)")
                if typ != "OK" or not msg_data:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = _decode_mime_header(msg.get("Subject", ""))
                from_ = _decode_mime_header(msg.get("From", ""))
                # Parse sender email
                sender_email = from_
                if "<" in from_ and ">" in from_:
                    sender_email = re.search(r"<([^>]+)>", from_).group(1).strip()
                else:
                    sender_email = from_.strip()
                message_id = msg.get("Message-ID", "").strip() or f"<{eid.decode()}-{mailbox_email}>"
                date_str = msg.get("Date")
                try:
                    from email.utils import parsedate_to_datetime
                    received_at = parsedate_to_datetime(date_str) if date_str else datetime.utcnow()
                except Exception:
                    received_at = datetime.utcnow()
                body = _extract_body(msg)
                body_preview = (body or "")[:300].replace("\n", " ")
                spam_label, spam_score, topic, mailbox_type = _classify_simple(subject, body, sender_email)
                sender_name = from_.replace(sender_email, "").strip(" <>\"'") or None
                results.append({
                    "message_id": message_id,
                    "sender": sender_email,
                    "sender_name": sender_name,
                    "subject": subject[:1024],
                    "body": body[:50000] if body else None,
                    "body_preview": body_preview[:500] if body_preview else None,
                    "received_at": received_at,
                    "spam_label": spam_label,
                    "spam_score": spam_score,
                    "topic": topic,
                    "mailbox_type": mailbox_type,
                    "attachment_count": sum(1 for p in (msg.walk() if msg.is_multipart() else [msg]) if p.get_content_disposition() == "attachment"),
                    "cc_count": len((msg.get("Cc") or "").split(",")) if msg.get("Cc") else 0,
                })
            except Exception:
                continue
        M.logout()
    except imaplib.IMAP4.error as e:
        err_str = str(e).lower()
        app_pass_required = (
            "application-specific password required" in err_str
            or "app password" in err_str
            or "authenticationfailed" in err_str
            or "invalid credentials" in err_str
        )
        if app_pass_required and ("gmail" in server.lower() or server == "imap.gmail.com"):
            raise ValueError(
                "Gmail requires an App Password, not your normal password. "
                "Turn on 2-Step Verification, then create one at: "
                "https://myaccount.google.com/apppasswords — use the 16-character password without spaces."
            )
        if app_pass_required:
            raise ValueError(
                "Use an App Password instead of your account password. "
                "Gmail: https://myaccount.google.com/apppasswords"
            )
        raise ValueError(f"IMAP login failed: {e}")
    except Exception as e:
        raise ValueError(f"IMAP error: {e}")
    return results


async def get_mailbox_for_user(db: AsyncSession, user_id: str) -> Optional[UserMailbox]:
    r = await db.execute(select(UserMailbox).where(UserMailbox.user_id == user_id, UserMailbox.is_active == True).limit(1))
    return r.scalar_one_or_none()


async def save_synced_emails(db: AsyncSession, user_id: str, emails: List[dict]) -> int:
    """Insert or replace synced emails (by user_id + message_id). Returns count saved."""
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    count = 0
    for row in emails:
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
            attachment_count=row.get("attachment_count", 0),
            cc_count=row.get("cc_count", 0),
        )
        db.add(rec)
        count += 1
    await db.flush()
    return count
