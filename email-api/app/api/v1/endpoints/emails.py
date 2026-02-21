"""Email list and detail endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.models import SyncedEmail
from app.models.email import Email, EmailReclassifyRequest
from app.services.email_service import generate_mock_emails, get_email_by_id
from app.services.imap_service import get_mailbox_for_user
from app.services.token_manager import get_oauth_for_user, get_valid_access_token
from app.services.gmail_service import sync_emails_gmail
from app.db.repositories.feedback import save_feedback

router = APIRouter()


def _synced_row_to_email(row: SyncedEmail) -> Email:
    return Email(
        message_id=row.message_id,
        sender=row.sender,
        sender_name=row.sender_name,
        subject=row.subject,
        body=row.body,
        body_preview=row.body_preview,
        timestamp=row.received_at.isoformat() if row.received_at else "",
        spam_label=row.spam_label,
        spam_score=row.spam_score,
        topic=row.topic,
        topic_confidence=row.topic_confidence,
        urgency_score=row.urgency_score,
        sentiment_score=row.sentiment_score,
        attachment_count=row.attachment_count,
        cc_count=row.cc_count,
        mailbox_type=row.mailbox_type,
    )


@router.get("/", response_model=dict)
async def get_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    topic: Optional[str] = None,
    spam_label: Optional[str] = None,
    sender: Optional[str] = None,
    search: Optional[str] = None,
    mailbox_type: Optional[str] = Query(None, description="Filter by mailbox: faculty | personal"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of emails. Uses synced emails when user has Gmail OAuth or IMAP mailbox, else mock."""
    user_id = current_user["id"]
    mailbox = await get_mailbox_for_user(db, user_id)
    oauth = await get_oauth_for_user(db, user_id)
    # Show synced emails if user has Gmail OAuth or IMAP mailbox
    if mailbox or oauth:
        base = select(SyncedEmail).where(SyncedEmail.user_id == user_id)
        if spam_label:
            base = base.where(SyncedEmail.spam_label == spam_label)
        if mailbox_type:
            base = base.where(SyncedEmail.mailbox_type == mailbox_type)
        if sender:
            base = base.where(SyncedEmail.sender.ilike(f"%{sender}%"))
        if search:
            base = base.where(or_(SyncedEmail.subject.ilike(f"%{search}%"), and_(SyncedEmail.body_preview.isnot(None), SyncedEmail.body_preview.ilike(f"%{search}%"))))
        total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
        q = base.order_by(SyncedEmail.received_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(q)
        rows = result.scalars().all()
        emails = [_synced_row_to_email(r) for r in rows]
        return {
            "emails": emails,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size else 0,
            "source": "gmail" if oauth and not mailbox else "mailbox",
        }
    emails, total = generate_mock_emails(
        user_email=current_user["email"],
        page=page,
        page_size=page_size,
        total_count=500,
        start_date=start_date,
        end_date=end_date,
        topic=topic,
        spam_label=spam_label,
        sender=sender,
        search=search,
        mailbox_type=mailbox_type,
    )
    return {
        "emails": emails,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "source": "demo",
    }


@router.post("/sync")
async def sync_emails(
    max_emails: int = Query(150, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync emails from Gmail API (OAuth users). Runs automatically after Google login. Returns count of new emails saved."""
    user_id = current_user["id"]
    access_token = await get_valid_access_token(db, user_id)
    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="No Gmail account connected. Sign in with Google to sync emails.",
        )
    try:
        saved = await sync_emails_gmail(db, user_id, access_token, max_emails=max_emails)
    except ValueError as e:
        logger.warning("Gmail sync ValueError for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Gmail sync failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail=f"Gmail sync error: {type(e).__name__}: {e}")
    return {"status": "synced", "new_saved": saved}


@router.get("/{message_id}", response_model=Email)
async def get_email_detail(
    message_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a specific email (from synced or mock)."""
    user_id = current_user["id"]
    r = await db.execute(
        select(SyncedEmail).where(SyncedEmail.user_id == user_id, SyncedEmail.message_id == message_id)
    )
    row = r.scalar_one_or_none()
    if row:
        return _synced_row_to_email(row)
    email = get_email_by_id(current_user["email"], message_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@router.post("/{message_id}/reclassify")
async def reclassify_email(
    message_id: str,
    request: EmailReclassifyRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reclassify email (feedback for model improvement)."""
    user_id = current_user["id"]
    r = await db.execute(
        select(SyncedEmail).where(SyncedEmail.user_id == user_id, SyncedEmail.message_id == message_id)
    )
    row = r.scalar_one_or_none()
    if row:
        current_label = row.spam_label
        row.spam_label = request.label
        await db.flush()
        await save_feedback(db, message_id=message_id, user_email=current_user["email"], original_label=current_label, corrected_label=request.label, reason=request.reason)
        return {"status": "success", "message": f"Email reclassified as {request.label}", "previous_label": current_label}
    email = get_email_by_id(current_user["email"], message_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    current_label = email.spam_label
    await save_feedback(db, message_id=message_id, user_email=current_user["email"], original_label=current_label, corrected_label=request.label, reason=request.reason)
    return {"status": "success", "message": f"Email reclassified as {request.label}", "previous_label": current_label}
