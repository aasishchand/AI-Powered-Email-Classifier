"""
Kafka batch consumer: consume from emails-raw, buffer, flush to MinIO as Parquet every 5 min or when batch size reached.
Commits offsets only after successful MinIO write (at-least-once). Failed messages go to DLQ path.
"""
import io
import json
import logging
import os
import time
import uuid
from datetime import datetime

import boto3
from confluent_kafka import Consumer, KafkaError, KafkaException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.environ.get("CONSUMER_BATCH_SIZE", "500"))
FLUSH_INTERVAL_SEC = int(os.environ.get("FLUSH_INTERVAL_SEC", "300"))
BUCKET_RAW = os.environ.get("MINIO_BUCKET_RAW", "emails-raw")
ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
ACCESS = os.environ.get("MINIO_ACCESS_KEY", os.environ.get("MINIO_ROOT_USER", "minioadmin"))
SECRET = os.environ.get("MINIO_SECRET_KEY", os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"))


def write_parquet_to_minio(records: list[dict], date: str, mailbox_type: str, batch_id: str) -> str:
    """Write records as Parquet to MinIO. Uses pyarrow or pandas; fallback JSON."""
    key = f"emails/ingestion_date={date}/mailbox_type={mailbox_type}/batch_{batch_id}.parquet"
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        table = pa.Table.from_pylist(records)
        buf = io.BytesIO()
        pq.write_table(table, buf)
        buf.seek(0)
        client = boto3.client(
            "s3",
            endpoint_url=ENDPOINT,
            aws_access_key_id=ACCESS,
            aws_secret_access_key=SECRET,
            region_name="us-east-1",
        )
        client.put_object(Bucket=BUCKET_RAW, Key=key, Body=buf.getvalue(), ContentType="application/octet-stream")
        logger.info("Wrote %d records to s3://%s/%s", len(records), BUCKET_RAW, key)
        return f"s3://{BUCKET_RAW}/{key}"
    except ImportError:
        key_json = key.replace(".parquet", ".json")
        client = boto3.client(
            "s3",
            endpoint_url=ENDPOINT,
            aws_access_key_id=ACCESS,
            aws_secret_access_key=SECRET,
            region_name="us-east-1",
        )
        body = json.dumps(records, default=str).encode("utf-8")
        client.put_object(Bucket=BUCKET_RAW, Key=key_json, Body=body, ContentType="application/json")
        logger.info("Wrote %d records (JSON) to s3://%s/%s", len(records), BUCKET_RAW, key_json)
        return f"s3://{BUCKET_RAW}/{key_json}"
    except Exception as e:
        logger.exception("MinIO write failed: %s", e)
        raise


def write_dlq(record: dict, reason: str):
    """Write failed message to DLQ prefix."""
    date = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"dlq/{date}/{uuid.uuid4().hex}.json"
    client = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS,
        aws_secret_access_key=SECRET,
        region_name="us-east-1",
    )
    payload = {"record": record, "reason": reason}
    client.put_object(
        Bucket=BUCKET_RAW,
        Key=key,
        Body=json.dumps(payload, default=str).encode("utf-8"),
        ContentType="application/json",
    )
    logger.warning("Wrote DLQ %s", key)


def run_consumer():
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.environ.get("KAFKA_TOPIC_EMAILS_RAW", "emails-raw")
    group = os.environ.get("KAFKA_CONSUMER_GROUP", "email-consumer-group")

    conf = {
        "bootstrap.servers": bootstrap,
        "group.id": group,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }
    consumer = Consumer(conf)
    consumer.subscribe([topic])

    buffer: list[dict] = []
    last_flush = time.monotonic()
    mailbox_type = os.environ.get("MAILBOX_TYPE", "faculty")

    while True:
        msg = consumer.poll(timeout=10.0)
        if msg is None:
            if buffer and (time.monotonic() - last_flush) >= FLUSH_INTERVAL_SEC:
                date = datetime.utcnow().strftime("%Y-%m-%d")
                batch_id = uuid.uuid4().hex
                try:
                    write_parquet_to_minio(buffer, date, mailbox_type, batch_id)
                    consumer.commit(msg=None)
                    buffer = []
                    last_flush = time.monotonic()
                except Exception as e:
                    logger.exception("Flush failed: %s", e)
                    for rec in buffer:
                        write_dlq(rec, str(e))
                    buffer = []
                    last_flush = time.monotonic()
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            logger.error("Consumer error: %s", msg.error())
            continue

        try:
            payload = json.loads(msg.value().decode("utf-8"))
            buffer.append(payload)
        except Exception as e:
            logger.warning("Bad message: %s", e)
            write_dlq({"raw": msg.value().decode("utf-8", errors="replace")}, str(e))
            consumer.commit(msg)
            continue

        if len(buffer) >= BATCH_SIZE:
            date = datetime.utcnow().strftime("%Y-%m-%d")
            batch_id = uuid.uuid4().hex
            try:
                write_parquet_to_minio(buffer, date, mailbox_type, batch_id)
                consumer.commit(msg)
                buffer = []
                last_flush = time.monotonic()
            except Exception as e:
                logger.exception("Batch write failed: %s", e)
                for rec in buffer:
                    write_dlq(rec, str(e))
                buffer = []
                last_flush = time.monotonic()


if __name__ == "__main__":
    run_consumer()
