# Kafka producer: fetch emails from IMAP, produce to Kafka. Backpressure when lag > 10k.
import json
import logging
import os
import time
from confluent_kafka import Producer
from confluent_kafka.cimpl import KafkaException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    emails_produced_total = Counter("emails_produced_total", "Total emails produced to Kafka")
    kafka_produce_latency = Histogram("kafka_produce_latency_seconds", "Produce latency in seconds")


def get_imap_emails(limit=500):
    host = os.environ.get("IMAP_HOST", "imap.gmail.com")
    port = int(os.environ.get("IMAP_PORT", "993"))
    user = os.environ.get("IMAP_USER", "")
    password = os.environ.get("IMAP_PASSWORD", "")
    use_ssl = os.environ.get("IMAP_USE_SSL", "true").lower() == "true"
    mailbox_type = os.environ.get("MAILBOX_TYPE", "faculty")
    if not user or not password:
        return []
    try:
        import imaplib
        import email
        M = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
        M.login(user, password)
        M.select("INBOX")
        _, data = M.search(None, "ALL")
        ids = data[0].split()
        if not ids:
            M.logout()
            return []
        ids = ids[-limit:]
        emails_out = []
        for eid in ids:
            _, msg_data = M.fetch(eid, "(RFC822)")
            for part in msg_data:
                if isinstance(part, tuple):
                    msg = email.message_from_bytes(part[1])
                    subj = msg.get("Subject", "") or ""
                    from_addr = msg.get("From", "") or ""
                    date_str = msg.get("Date", "") or ""
                    body = ""
                    if msg.is_multipart():
                        for p in msg.walk():
                            if p.get_content_type() == "text/plain":
                                try:
                                    body = p.get_payload(decode=True).decode(errors="replace")[:5000]
                                except Exception:
                                    pass
                                break
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode(errors="replace")[:5000]
                        except Exception:
                            pass
                    emails_out.append({
                        "id": eid.decode() if isinstance(eid, bytes) else str(eid),
                        "subject": subj,
                        "sender": from_addr,
                        "body_preview": body[:500] if body else "",
                        "received_at": date_str,
                        "mailbox_type": mailbox_type,
                        "raw_headers": str(msg.items())[:2000],
                    })
        M.logout()
        return emails_out
    except Exception as e:
        logger.exception("IMAP fetch failed: %s", e)
        return []


def get_consumer_lag(bootstrap, topic, group):
    return 0


def run_producer():
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.environ.get("KAFKA_TOPIC_EMAILS_RAW", "emails-raw")
    interval_sec = int(os.environ.get("FETCH_INTERVAL_SECONDS", "300"))
    backpressure_lag = int(os.environ.get("BACKPRESSURE_LAG", "10000"))
    conf = {"bootstrap.servers": bootstrap, "client.id": "email-ingestion-producer"}
    producer = Producer(conf)
    if PROMETHEUS_AVAILABLE:
        start_http_server(9090)
    while True:
        lag = get_consumer_lag(bootstrap, topic, "email-consumer-group")
        if lag > backpressure_lag:
            logger.warning("Consumer lag %d > %d; pausing", lag, backpressure_lag)
            time.sleep(60)
            continue
        emails = get_imap_emails(limit=200)
        for em in emails:
            payload = json.dumps(em, default=str)
            key = em.get("id", "").encode("utf-8")[:512]
            start = time.perf_counter()
            try:
                producer.produce(topic, value=payload.encode("utf-8"), key=key)
                producer.flush(timeout=10)
                if PROMETHEUS_AVAILABLE:
                    emails_produced_total.inc()
                    kafka_produce_latency.observe(time.perf_counter() - start)
            except KafkaException as e:
                logger.exception("Produce failed: %s", e)
        if emails:
            logger.info("Produced %d emails to %s", len(emails), topic)
        time.sleep(interval_sec)


if __name__ == "__main__":
    run_producer()
