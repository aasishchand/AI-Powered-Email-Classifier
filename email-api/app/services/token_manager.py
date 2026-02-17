"""OAuth token storage and refresh. Tokens are encrypted at rest."""
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.encryption import decrypt_password, encrypt_password
from app.db.models import UserOAuth

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


async def get_oauth_for_user(db: AsyncSession, user_id: str) -> Optional[UserOAuth]:
    """Get OAuth record for user (Google)."""
    r = await db.execute(select(UserOAuth).where(UserOAuth.user_id == user_id, UserOAuth.provider == "google").limit(1))
    return r.scalar_one_or_none()


async def get_valid_access_token(db: AsyncSession, user_id: str) -> Optional[str]:
    """
    Return a valid access token for the user. Refreshes using refresh_token if expired.
    Returns None if no OAuth or refresh failed.
    """
    oauth = await get_oauth_for_user(db, user_id)
    if not oauth:
        return None
    access = _decrypt(oauth.access_token_encrypted)
    refresh_enc = oauth.refresh_token_encrypted
    expires_at = oauth.expires_at
    # Consider expired 60s before actual expiry to avoid race
    now = datetime.now(timezone.utc)
    if expires_at and (expires_at.timestamp() - 60) > now.timestamp() and access:
        return access
    if not refresh_enc:
        return access  # no refresh token, return current (might be invalid)
    new_access, new_expires = await _refresh_google_token(_decrypt(refresh_enc))
    if not new_access:
        return access
    oauth.access_token_encrypted = _encrypt(new_access)
    if new_expires:
        oauth.expires_at = new_expires
    await db.flush()
    return new_access


def _encrypt(plain: str) -> str:
    return encrypt_password(plain)


def _decrypt(encrypted: str) -> str:
    return decrypt_password(encrypted)


async def _refresh_google_token(refresh_token: str) -> tuple[Optional[str], Optional[datetime]]:
    """Exchange refresh_token for new access_token. Returns (access_token, expires_at)."""
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return None, None
    async with httpx.AsyncClient() as client:
        r = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if r.status_code != 200:
        return None, None
    data = r.json()
    access = data.get("access_token")
    expires_in = data.get("expires_in")
    expires_at = None
    if expires_in:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    return access, expires_at


async def save_google_tokens(
    db: AsyncSession,
    user_id: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_in_seconds: Optional[int],
) -> None:
    """Upsert Google OAuth tokens for user (encrypted)."""
    from datetime import timedelta
    r = await db.execute(select(UserOAuth).where(UserOAuth.user_id == user_id, UserOAuth.provider == "google").limit(1))
    row = r.scalar_one_or_none()
    expires_at = None
    if expires_in_seconds:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    if row:
        row.access_token_encrypted = _encrypt(access_token)
        row.refresh_token_encrypted = _encrypt(refresh_token) if refresh_token else row.refresh_token_encrypted
        row.expires_at = expires_at
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = UserOAuth(
            user_id=user_id,
            provider="google",
            access_token_encrypted=_encrypt(access_token),
            refresh_token_encrypted=_encrypt(refresh_token) if refresh_token else None,
            expires_at=expires_at,
        )
        db.add(row)
    await db.flush()
