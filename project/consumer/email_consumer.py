"""Kafka consumer that classifies emails and stores predictions in PostgreSQL."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from kafka import KafkaConsumer
from kafka.admin import KafkaAdminClient
from sqlalchemy.exc import IntegrityError

from project.database import db
from project.model.model_service import predict_email
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


def _parse_timestamp(raw_ts: str) -> datetime:
    """Parse ISO-8601 timestamp string to datetime."""
    try:
        return datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError(f"Invalid timestamp format: {raw_ts}") from exc


def run_consumer() -> None:
    """Consume emails from Kafka, classify, and persist records."""
    db.init_db()
    check_kafka_connection()

    consumer = KafkaConsumer(
        config.KAFKA_TOPIC,
        bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset=config.KAFKA_AUTO_OFFSET_RESET,
        enable_auto_commit=True,
        group_id="email-classifier-consumer-group",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    logger.info("Consumer started topic=%s", config.KAFKA_TOPIC)
    try:
        for message in consumer:
            try:
                payload: dict[str, Any] = message.value
                email_id = str(payload["email_id"])
                text = str(payload["text"])
                timestamp = _parse_timestamp(str(payload["timestamp"]))

                label, confidence = predict_email(text)
                src = payload.get("pipeline_source")
                if not src:
                    src = "unknown"
                record = {
                    "email_id": email_id,
                    "text": text,
                    "predicted_label": label,
                    "confidence": confidence,
                    "timestamp": timestamp,
                    "pipeline_source": str(src)[:32],
                }
                try:
                    db.insert_email(record)
                except IntegrityError:
                    logger.info("[CONSUMER] duplicate email_id=%s skipped", email_id)
                    continue
                logger.info(
                    "[CONSUMER] email_id=%s | predicted=%s | confidence=%.2f | stored ok",
                    email_id,
                    label,
                    confidence,
                )
            except Exception as exc:
                logger.exception("Per-message processing failed: %s", exc)
                continue
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user, shutting down.")
    finally:
        consumer.close()
        logger.info("Consumer closed cleanly.")


if __name__ == "__main__":
    run_consumer()
