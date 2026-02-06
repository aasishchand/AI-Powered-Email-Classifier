"""Email listing and reclassification service. Uses mock data when warehouse unavailable."""
import random
from datetime import datetime, timedelta
from typing import List, Optional

from app.models.email import Email


# Faculty/work senders
SENDERS_FACULTY = [
    "registrar@university.edu",
    "hr@university.edu",
    "research@university.edu",
    "it-support@university.edu",
    "events@university.edu",
    "dean@college.edu",
    "student@university.edu",
    "external@company.com",
]
# Personal senders (Gmail, Outlook, etc.)
SENDERS_PERSONAL = [
    "friend@gmail.com",
    "family@outlook.com",
    "newsletter@substack.com",
    "shopping@amazon.com",
    "bank@chase.com",
    "doctor@clinic.org",
    "travel@booking.com",
    "social@linkedin.com",
]
SENDERS = SENDERS_FACULTY + SENDERS_PERSONAL
PERSONAL_TOPICS = ["Personal", "Shopping", "Newsletter", "Social", "Travel", "Finance - Personal", "Health"]
TOPICS = [
    "Academic - Course Materials",
    "Administrative - HR & Policies",
    "Research - Grant Opportunities",
    "Events - Seminars & Conferences",
    "IT - Technical Announcements",
    "Finance - Budget & Funding",
    "Student Affairs",
    "General Announcements",
]
SUBJECTS_FACULTY = [
    "Re: Course syllabus update",
    "Reminder: Faculty meeting tomorrow",
    "Grant deadline extension",
    "Campus event invitation",
    "IT maintenance notice",
    "Budget approval request",
    "Student inquiry",
    "Weekly digest",
]
SUBJECTS_PERSONAL = [
    "Weekend plans",
    "Your order has shipped",
    "Newsletter: Weekly digest",
    "Meeting tomorrow?",
    "Family reunion save the date",
    "Account statement",
    "Reminder: Doctor appointment",
    "Invitation to connect",
]
SUBJECTS = SUBJECTS_FACULTY + SUBJECTS_PERSONAL


def generate_mock_emails(
    user_email: str,
    page: int,
    page_size: int,
    total_count: int = 500,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    topic: Optional[str] = None,
    spam_label: Optional[str] = None,
    sender: Optional[str] = None,
    search: Optional[str] = None,
    mailbox_type: Optional[str] = None,
) -> tuple:
    """Generate paginated mock emails (faculty + personal). In production would query Hive/Spark."""
    emails: List[Email] = []
    base = (page - 1) * page_size
    for i in range(page_size):
        idx = base + i
        if idx >= total_count:
            break
        is_personal = random.random() < 0.45  # ~45% personal, 55% faculty
        if mailbox_type == "personal":
            is_personal = True
        elif mailbox_type == "faculty":
            is_personal = False
        send_addr = random.choice(SENDERS_PERSONAL if is_personal else SENDERS_FACULTY)
        subj = random.choice(SUBJECTS_PERSONAL if is_personal else SUBJECTS_FACULTY)
        t = random.choice(PERSONAL_TOPICS if is_personal else TOPICS)
        ts = datetime.utcnow() - timedelta(days=idx % 30, hours=idx % 24)
        is_spam = random.random() < 0.08
        label = "spam" if is_spam else "ham"
        body_preview = ("This is a sample email body preview for development. " * 3)[:200]
        emails.append(
            Email(
                message_id=f"<mock-{idx}@university.edu>",
                sender=send_addr,
                sender_name=send_addr.split("@")[0].replace(".", " ").title(),
                subject=subj,
                body_preview=body_preview,
                timestamp=ts.isoformat(),
                spam_label=label,
                spam_score=0.92 if is_spam else 0.05,
                topic=t,
                topic_confidence=round(random.uniform(0.7, 0.99), 2),
                urgency_score=round(random.uniform(0.1, 0.9), 2),
                sentiment_score=round(random.uniform(-0.3, 0.5), 2),
                attachment_count=random.randint(0, 3),
                cc_count=random.randint(0, 5),
                mailbox_type="personal" if is_personal else "faculty",
            )
        )
    return emails, total_count


def get_email_by_id(user_email: str, message_id: str) -> Optional[Email]:
    """Get single email. In production would query warehouse."""
    # Mock: return one fake email for any requested id
    return Email(
        message_id=message_id,
        sender="sender@university.edu",
        sender_name="Sender Name",
        subject="Sample email subject",
        body="Full email body content for development and testing.",
        body_preview="Full email body content for development.",
        timestamp=(datetime.utcnow() - timedelta(days=1)).isoformat(),
        spam_label="ham",
        spam_score=0.12,
        topic="Academic - Course Materials",
        topic_confidence=0.88,
        urgency_score=0.5,
        sentiment_score=0.2,
        attachment_count=1,
        cc_count=2,
        mailbox_type="faculty",
    )
