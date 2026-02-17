"""Real-time email ingestion via IMAP (e.g. Gmail with App Password)."""
import email
import imaplib
import re
import socket
from datetime import datetime
from email.header import decode_header
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_password
from app.db.models import SyncedEmail, UserMailbox

# Connection timeout for IMAP (seconds)
IMAP_TIMEOUT = 25

# Default IMAP servers
IMAP_SERVERS = {
    "gmail.com": ("imap.gmail.com", 993),
    "googlemail.com": ("imap.gmail.com", 993),
    "outlook.com": ("outlook.office365.com", 993),
    "hotmail.com": ("outlook.office365.com", 993),
    "live.com": ("outlook.office365.com", 993),
    "yahoo.com": ("imap.mail.yahoo.com", 993),
    "icloud.com": ("imap.mail.me.com", 993),
}


def _get_imap_server(mailbox_email: str) -> Tuple[str, int]:
    domain = mailbox_email.split("@")[-1].lower() if "@" in mailbox_email else ""
    return IMAP_SERVERS.get(domain, ("imap.gmail.com", 993))


def _normalize_imap_server(
    mailbox_email: str,
    imap_server: Optional[str],
    imap_port: int,
) -> Tuple[str, int]:
    """Ensure we always have a valid host and port. Empty or invalid server -> use known host from email."""
    if imap_server and str(imap_server).strip():
        return str(imap_server).strip(), imap_port
    return _get_imap_server(mailbox_email)


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


def _strip_html_to_plain(text: str, max_len: int = 50000) -> str:
    """Convert HTML to plain text so it displays as readable content, not raw source."""
    if not text or not isinstance(text, str):
        return ""
    # Remove script/style and strip tags; collapse whitespace
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


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
                    raw = part.get_payload(decode=True).decode(errors="replace")
                    body = _strip_html_to_plain(raw, max_len=50000)
                    break
                except Exception:
                    pass
    else:
        try:
            raw = msg.get_payload(decode=True)
            if raw:
                body = raw.decode(errors="replace")
            else:
                body = str(msg.get_payload() or "")
        except Exception:
            body = str(msg.get_payload())[:2000]
        ct = msg.get_content_type()
        if ct == "text/html" or ("<" in body and ">" in body):
            body = _strip_html_to_plain(body, max_len=50000)
    return (body or "")[:50000]


def _urgency_simple(subject: str, body: str) -> float:
    """Rule-based urgency score 0.0–1.0 from subject and body. Replace with ML later."""
    text = (subject + " " + (body or ""))[:10000].lower()
    score = 0.3  # baseline
    high = ["urgent", "asap", "as soon as possible", "deadline", "due today", "due tomorrow", "reply requested", "time sensitive", "action required", "immediately", "critical", "emergency"]
    medium = ["important", "reminder", "meeting in", "follow up", "response needed", "please respond", "confirm by", "reminder:"]
    for phrase in high:
        if phrase in text:
            score = min(1.0, score + 0.35)
    for phrase in medium:
        if phrase in text:
            score = min(1.0, score + 0.2)
    return round(min(1.0, max(0.0, score)), 2)


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
    server, port = _normalize_imap_server(mailbox_email, imap_server, imap_port)
    results = []
    try:
        if port == 993:
            M = imaplib.IMAP4_SSL(server, port=port, timeout=IMAP_TIMEOUT)
        else:
            M = imaplib.IMAP4(server, port=port, timeout=IMAP_TIMEOUT)
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
                urgency_score = _urgency_simple(subject, body)
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
                    "urgency_score": urgency_score,
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
    except (socket.gaierror, OSError) as e:
        errno = getattr(e, "errno", None)
        if errno == 11001 or "getaddrinfo" in str(e).lower():
            raise ValueError(
                "Could not reach the email server (DNS failed). Check your internet connection, "
                "and that your email provider (e.g. Gmail, Outlook) is not blocked by your network."
            )
        raise ValueError(f"Network error connecting to {server}: {e}")
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
            urgency_score=row.get("urgency_score", 0.3),
            attachment_count=row.get("attachment_count", 0),
            cc_count=row.get("cc_count", 0),
        )
        db.add(rec)
        count += 1
    await db.flush()
    return count
