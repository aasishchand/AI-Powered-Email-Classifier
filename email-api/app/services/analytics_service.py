"""Analytics and dashboard metrics service. Uses mock data when Spark/Hive unavailable."""
from datetime import date
from typing import List

from app.models.metrics import DashboardMetrics, EmailTrend, TopicInfo


def get_dashboard_metrics_for_user(
    user_email: str, start_date: date, end_date: date
) -> DashboardMetrics:
    """Return dashboard metrics. In production this would query Hive/Spark."""
    total_emails = 1247
    spam_count = 89
    spam_percentage = round(spam_count / total_emails * 100, 2) if total_emails else 0
    time_saved_hours = round(spam_count * 0.5 / 60, 2)
    top_topics = [
        TopicInfo(name="Academic - Course Materials", category="Academic", count=312),
        TopicInfo(name="Administrative - HR & Policies", category="Admin", count=198),
        TopicInfo(name="Research - Grant Opportunities", category="Research", count=156),
        TopicInfo(name="Events - Seminars & Conferences", category="Events", count=134),
        TopicInfo(name="IT - Technical Announcements", category="IT", count=98),
        TopicInfo(name="Finance - Budget & Funding", category="Finance", count=87),
        TopicInfo(name="Student Affairs", category="Academic", count=76),
        TopicInfo(name="General Announcements", category="Admin", count=65),
        TopicInfo(name="Collaborations", category="Research", count=54),
        TopicInfo(name="Library Services", category="Admin", count=43),
    ]
    return DashboardMetrics(
        total_emails=total_emails,
        spam_count=spam_count,
        spam_percentage=spam_percentage,
        avg_sentiment=0.12,
        avg_urgency=0.45,
        top_topics=top_topics,
        time_saved_hours=time_saved_hours,
        avg_response_time=12.5,
        change_from_yesterday=5.2,
        avg_email_length=342,
    )


def get_email_trends_for_user(user_email: str, days: int) -> List[EmailTrend]:
    """Return daily email trends. In production would query warehouse."""
    from datetime import timedelta
    trends = []
    end = date.today()
    for i in range(days - 1, -1, -1):
        d = end - timedelta(days=i)
        total = 40 + (i % 20) * 3
        spam = total // 10
        urgent = total // 5
        trends.append(
            EmailTrend(date=d, total=total, spam=spam, ham=total - spam, urgent=urgent)
        )
    return trends
