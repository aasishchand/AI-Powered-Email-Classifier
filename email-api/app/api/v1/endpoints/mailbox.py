"""Connect mailbox (IMAP) and sync emails in real time."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_user
from app.core.encryption import decrypt_password, encrypt_password
from app.db.session import get_db
from app.db.models import UserMailbox
from app.services.token_manager import get_oauth_for_user
from app.services.imap_service import (
    fetch_emails_imap,
    get_mailbox_for_user,
    save_synced_emails,
    _normalize_imap_server,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class ConnectMailboxRequest(BaseModel):
    email: EmailStr
    app_password: str  # Gmail App Password or account password
    imap_server: Optional[str] = None
    imap_port: int = 993


class MailboxStatusResponse(BaseModel):
    connected: bool
    method: Optional[str] = None  # "gmail" | "imap"
    mailbox_email: Optional[str] = None
    last_sync: Optional[str] = None


@router.post("/connect")
async def connect_mailbox(
    body: ConnectMailboxRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect your email (Gmail/Outlook) for real-time sync. Use App Password for Gmail."""
    try:
        user_id = current_user["id"]
        # Normalize App Password (Gmail shows it with spaces; IMAP expects no spaces)
        app_password = (body.app_password or "").replace(" ", "").strip()
        if not app_password:
            raise HTTPException(status_code=400, detail="App password is required.")

        # Deactivate any existing
        await db.execute(select(UserMailbox).where(UserMailbox.user_id == user_id))
        existing = await get_mailbox_for_user(db, user_id)
        if existing:
            existing.is_active = False
            await db.flush()

        # Test IMAP connection first
        try:
            fetch_emails_imap(
                body.email,
                app_password,
                body.imap_server,
                body.imap_port,
                max_emails=1,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Connection failed: {e}")

        # Encrypt and save
        try:
            enc = encrypt_password(app_password)
        except ValueError as e:
            raise HTTPException(status_code=500, detail="Server encryption error. Please try again.")

        server, port = _normalize_imap_server(body.email, body.imap_server, body.imap_port)
        mailbox = UserMailbox(
            user_id=user_id,
            mailbox_email=body.email,
            encrypted_password=enc,
            imap_server=server,
            imap_port=port,
            use_ssl=True,
        )
        db.add(mailbox)
        await db.flush()
        return {"status": "connected", "mailbox_email": body.email}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post("/sync")
async def sync_mailbox(
    max_emails: int = 50,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch latest emails from connected mailbox and classify them."""
    mailbox = await get_mailbox_for_user(db, current_user["id"])
    if not mailbox:
        raise HTTPException(status_code=400, detail="No mailbox connected. Connect in Settings first.")
    password = decrypt_password(mailbox.encrypted_password)
    try:
        emails = fetch_emails_imap(
            mailbox.mailbox_email,
            password,
            mailbox.imap_server,
            mailbox.imap_port,
            max_emails=max_emails,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    count = await save_synced_emails(db, current_user["id"], emails)
    return {"status": "synced", "fetched": len(emails), "new_saved": count}


@router.get("/status", response_model=MailboxStatusResponse)
async def mailbox_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if user has email connected: Gmail OAuth (preferred) or IMAP."""
    user_id = current_user["id"]
    # Prefer Gmail OAuth when present (no app password needed)
    oauth = await get_oauth_for_user(db, user_id)
    if oauth:
        return MailboxStatusResponse(
            connected=True,
            method="gmail",
            mailbox_email=current_user.get("email"),
        )
    mailbox = await get_mailbox_for_user(db, user_id)
    if not mailbox:
        return MailboxStatusResponse(connected=False)
    return MailboxStatusResponse(
        connected=True,
        method="imap",
        mailbox_email=mailbox.mailbox_email,
    )


@router.delete("/disconnect")
async def disconnect_mailbox(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect and stop syncing this mailbox."""
    mailbox = await get_mailbox_for_user(db, current_user["id"])
    if mailbox:
        mailbox.is_active = False
        await db.flush()
    return {"status": "disconnected"}
