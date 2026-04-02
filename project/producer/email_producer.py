"""Kafka producer that simulates a realistic email stream."""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient

from project.utils.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

def check_kafka_connection() -> None:
    """Exit early if Kafka is not reachable (local Windows Kafka)."""
    try:
        admin = KafkaAdminClient(bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS)
        admin.close()
        logger.info("✅ Kafka connection successful at %s", config.KAFKA_BOOTSTRAP_SERVERS)
    except Exception:
        logger.error("❌ Cannot connect to Kafka at %s — Is C:\\kafka running?", config.KAFKA_BOOTSTRAP_SERVERS)
        logger.error("   Start it with: .\\bin\\windows\\kafka-server-start.bat .\\config\\server.properties")
        raise SystemExit(1)


def _sample_emails() -> list[str]:
    """Return exactly 10 sample email texts (spam, legitimate, ambiguous)."""
    return [
        # 4 spam
        "Congratulations! You won a $10,000 gift card. Click here to claim now.",
        "URGENT OFFER: Limited-time investment scheme with guaranteed 300% return. Act now!",
        "Security alert: your account will be suspended. Verify your password immediately at this link.",
        "Exclusive pharmacy deal: buy now and save 80%. No prescription needed.",
        # 4 legitimate
        "Team meeting invite: Please join the project sprint planning at 10:00 AM tomorrow.",
        "Project update: The ETL pipeline changes have been merged; review the release notes.",
        "Invoice #48219 for February cloud hosting charges is attached for your approval.",
        "Reminder: Quarterly performance review discussion scheduled for Friday afternoon.",
        # 2 ambiguous
        "Weekly newsletter: Product updates and engineering highlights. Unsubscribe anytime.",
        "Special member promotion: You are eligible for a discounted annual subscription renewal.",
    ]


def _build_payload(text: str) -> dict[str, Any]:
    """Create a single Kafka payload for an email event."""
    return {
        "email_id": str(uuid4()),
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_source": "synthetic",
    }


def run_producer(delay_seconds: float = 2.0, once: bool = False) -> None:
    """Produce sample emails to Kafka: continuous stream by default, or one batch with ``once=True``."""
    check_kafka_connection()
    producer = KafkaProducer(
        bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=5,
        request_timeout_ms=30000,
    )

    samples = _sample_emails()

    def send_one(text: str) -> None:
        payload = _build_payload(text)
        producer.send(config.KAFKA_TOPIC, payload)
        logger.info(
            "[PRODUCER] Sent email_id=%s at %s",
            payload["email_id"],
            payload["timestamp"],
        )

    try:
        if once:
            for text in samples:
                send_one(text)
                time.sleep(max(delay_seconds, 0.0))
        else:
            logger.info("Real-time producer running (Ctrl+C to stop); interval=%ss", delay_seconds)
            while True:
                send_one(random.choice(samples))
                time.sleep(max(delay_seconds, 0.0))
    except KeyboardInterrupt:
        logger.info("Producer stopped by user.")
    except Exception:
        logger.exception("Producer failed while sending messages.")
        raise
    finally:
        producer.flush()
        producer.close()
        logger.info("Producer flushed and closed cleanly.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream synthetic emails to Kafka.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Send the fixed batch of 10 messages then exit (smoke test).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between messages (default: 2).",
    )
    args = parser.parse_args()
    run_producer(delay_seconds=args.interval, once=args.once)
