"""Utility to verify local Kafka is reachable before running producer/consumer.

Run directly:
    python -m project.utils.kafka_check
"""

from __future__ import annotations

import logging

from kafka.admin import KafkaAdminClient

from project.utils.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def check_kafka() -> None:
    """Fail fast if Kafka is not reachable; warn if topic missing."""
    try:
        admin = KafkaAdminClient(bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS)
        topics = admin.list_topics()
        admin.close()
        logger.info("✅ Kafka is running at %s", config.KAFKA_BOOTSTRAP_SERVERS)
        if config.KAFKA_TOPIC in topics:
            logger.info("✅ Topic '%s' exists", config.KAFKA_TOPIC)
        else:
            logger.warning(
                "⚠️  Topic '%s' not found. Create it with:\n"
                r"   C:\kafka\bin\windows\kafka-topics.bat "
                "--create --topic %s --bootstrap-server localhost:9092 "
                "--partitions 1 --replication-factor 1",
                config.KAFKA_TOPIC,
                config.KAFKA_TOPIC,
            )
    except Exception:
        logger.error("❌ Kafka not reachable at %s", config.KAFKA_BOOTSTRAP_SERVERS)
        logger.error("   Make sure both terminals are running:")
        logger.error(r"   Terminal 1: C:\kafka\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties")
        logger.error(r"   Terminal 2: C:\kafka\bin\windows\kafka-server-start.bat .\config\server.properties")
        raise SystemExit(1)


if __name__ == "__main__":
    check_kafka()
