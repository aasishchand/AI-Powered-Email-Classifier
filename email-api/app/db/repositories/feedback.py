"""User feedback repository for reclassification."""
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserFeedback


async def save_feedback(
    db: AsyncSession,
    message_id: str,
    user_email: str,
    original_label: str,
    corrected_label: str,
    reason: Optional[str] = None,
) -> UserFeedback:
    fb = UserFeedback(
        message_id=message_id,
        user_email=user_email,
        original_label=original_label,
        corrected_label=corrected_label,
        reason=reason,
    )
    db.add(fb)
    await db.flush()
    await db.refresh(fb)
    return fb
