"""Analytics and dashboard metrics service. Queries real SyncedEmail data from DB."""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, func, case, and_, String, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SyncedEmail
from app.models.metrics import DashboardMetrics, EmailTrend, TopicInfo

logger = logging.getLogger(__name__)


def _date_col():
    """SQLite-compatible: extract date string (YYYY-MM-DD) from received_at."""
    return func.substr(func.cast(SyncedEmail.received_at, String), 1, 10)


async def get_dashboard_metrics(
    db: AsyncSession,
    user_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> DashboardMetrics:
    """Compute dashboard metrics from real synced emails for the given user."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    base = SyncedEmail.user_id == user_id

    # ---- Total emails ----
    total_emails = (await db.execute(
        select(func.count()).where(base)
    )).scalar() or 0

    # ---- Spam count ----
    spam_count = (await db.execute(
        select(func.count()).where(base, SyncedEmail.spam_label == "spam")
    )).scalar() or 0
    spam_percentage = round(spam_count / total_emails * 100, 2) if total_emails else 0.0

    # ---- Averages (urgency, sentiment) ----
    avg_row = (await db.execute(
        select(
            func.coalesce(func.avg(SyncedEmail.urgency_score), 0.0),
            func.coalesce(func.avg(SyncedEmail.sentiment_score), 0.0),
        ).where(base)
    )).one()
    avg_urgency = round(float(avg_row[0]), 2)
    avg_sentiment = round(float(avg_row[1]), 2)

    # ---- Average email body length ----
    avg_email_length = int((await db.execute(
        select(func.coalesce(func.avg(func.length(SyncedEmail.body)), 0)).where(base)
    )).scalar() or 0)

    # ---- Top topics ----
    topic_rows = (await db.execute(
        select(SyncedEmail.topic, func.count().label("cnt"))
        .where(base, SyncedEmail.topic.isnot(None))
        .group_by(SyncedEmail.topic)
        .order_by(func.count().desc())
        .limit(10)
    )).all()
    top_topics = [TopicInfo(name=name, category=_topic_to_category(name), count=cnt) for name, cnt in topic_rows]

    # ---- Time saved (estimated: each spam email saves ~30s of user time) ----
    time_saved_hours = round(spam_count * 0.5 / 60, 2)

    # ---- Change from yesterday (SQLite-compatible date comparison) ----
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    today_count = (await db.execute(
        select(func.count()).where(base, _date_col() == today_str)
    )).scalar() or 0

    yesterday_count = (await db.execute(
        select(func.count()).where(base, _date_col() == yesterday_str)
    )).scalar() or 0

    if yesterday_count > 0:
        change = round((today_count - yesterday_count) / yesterday_count * 100, 1)
    else:
        change = 100.0 if today_count > 0 else 0.0

    # ---- Avg response time (estimated from avg time between consecutive emails) ----
    avg_response_time = await _estimate_avg_response_hours(db, user_id)

    return DashboardMetrics(
        total_emails=total_emails,
        spam_count=spam_count,
        spam_percentage=spam_percentage,
        avg_sentiment=avg_sentiment,
        avg_urgency=avg_urgency,
        top_topics=top_topics,
        time_saved_hours=time_saved_hours,
        avg_response_time=avg_response_time,
        change_from_yesterday=change,
        avg_email_length=avg_email_length,
    )


async def get_email_trends(
    db: AsyncSession,
    user_id: str,
    days: int = 30,
) -> List[EmailTrend]:
    """Compute daily email trends from real synced emails grouped by received_at date."""
    end = date.today()
    start = end - timedelta(days=days - 1)

    date_expr = _date_col()

    q = (
        select(
            date_expr.label("day"),
            func.count().label("total"),
            func.sum(case((SyncedEmail.spam_label == "spam", 1), else_=0)).label("spam"),
            func.sum(case((SyncedEmail.spam_label != "spam", 1), else_=0)).label("ham"),
            func.sum(case((SyncedEmail.urgency_score > 0.6, 1), else_=0)).label("urgent"),
        )
        .where(
            SyncedEmail.user_id == user_id,
            date_expr >= start.isoformat(),
            date_expr <= end.isoformat(),
        )
        .group_by(date_expr)
        .order_by(date_expr)
    )
    rows = (await db.execute(q)).all()
    row_map = {str(r.day): r for r in rows}

    trends: List[EmailTrend] = []
    for i in range(days):
        d = start + timedelta(days=i)
        d_str = d.isoformat()
        r = row_map.get(d_str)
        trends.append(EmailTrend(
            date=d,
            total=int(r.total) if r else 0,
            spam=int(r.spam) if r else 0,
            ham=int(r.ham) if r else 0,
            urgent=int(r.urgent) if r else 0,
        ))
    return trends


async def get_email_heatmap(
    db: AsyncSession,
    user_id: str,
) -> list:
    """Compute heatmap from real received_at data (hour vs day of week).
    Uses strftime for SQLite compatibility.
    """
    # SQLite: strftime('%w', col) = day of week (0=Sunday), strftime('%H', col) = hour
    dow_expr = func.cast(func.strftime("%w", SyncedEmail.received_at), String)
    hour_expr = func.cast(func.strftime("%H", SyncedEmail.received_at), String)

    q = (
        select(
            dow_expr.label("dow"),
            hour_expr.label("hour"),
            func.count().label("volume"),
        )
        .where(SyncedEmail.user_id == user_id)
        .group_by(dow_expr, hour_expr)
    )

    rows = (await db.execute(q)).all()
    heatmap = {}
    for r in rows:
        try:
            heatmap[(int(r.dow), int(r.hour))] = int(r.volume)
        except (ValueError, TypeError):
            pass

    data = []
    for d in range(7):
        for h in range(24):
            data.append({"day": d + 1, "hour": h, "volume": heatmap.get((d, h), 0)})
    return data


def _topic_to_category(topic_name: str) -> str:
    """Map topic name to a short category for pie chart grouping."""
    t = (topic_name or "").lower()
    if "academic" in t or "course" in t or "student" in t or "syllabus" in t:
        return "Academic"
    if "research" in t or "grant" in t or "paper" in t:
        return "Research"
    if "event" in t or "seminar" in t or "conference" in t:
        return "Events"
    if "admin" in t or "hr" in t or "policy" in t or "announcement" in t:
        return "Admin"
    if "it" in t or "technical" in t:
        return "IT"
    if "finance" in t or "budget" in t:
        return "Finance"
    if "shop" in t or "order" in t:
        return "Shopping"
    if "newsletter" in t or "subscribe" in t:
        return "Newsletter"
    return "General"


async def _estimate_avg_response_hours(db: AsyncSession, user_id: str) -> float:
    """Estimate avg time between incoming emails (as a proxy for 'response time')."""
    row = (await db.execute(
        select(
            func.min(SyncedEmail.received_at),
            func.max(SyncedEmail.received_at),
            func.count(),
        ).where(SyncedEmail.user_id == user_id)
    )).one()
    min_at, max_at, count = row
    if not min_at or not max_at or count < 2:
        return 0.0
    # Handle both datetime objects and strings (SQLite returns strings)
    if isinstance(min_at, str):
        try:
            min_at = datetime.fromisoformat(min_at)
            max_at = datetime.fromisoformat(max_at)
        except Exception:
            return 0.0
    span = (max_at - min_at).total_seconds()
    avg_gap_hours = span / (count - 1) / 3600
    return round(avg_gap_hours, 1)
