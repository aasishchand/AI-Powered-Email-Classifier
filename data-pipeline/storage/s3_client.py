"""S3-compatible (MinIO) client for email pipeline storage operations."""
import json
import logging
import os
import uuid
from typing import Any

import boto3
import pandas as pd
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Load from env (same names as docker-compose / .env.bigdata)
ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", os.environ.get("MINIO_ROOT_USER", "minioadmin"))
SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"))
BUCKET_RAW = os.environ.get("MINIO_BUCKET_RAW", "emails-raw")
BUCKET_PROCESSED = os.environ.get("MINIO_BUCKET_PROCESSED", "emails-processed")
BUCKET_MODELS = os.environ.get("MINIO_BUCKET_MODELS", "email-models")

# Use path-style for MinIO (no virtual-hosted style)
USE_PATH_STYLE = True


def _client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
        use_ssl=ENDPOINT.startswith("https"),
    )


def _resource():
    return boto3.resource(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
        use_ssl=ENDPOINT.startswith("https"),
    )


def upload_emails_batch(
    emails: list[dict[str, Any]],
    date: str,
    mailbox_type: str,
) -> str:
    """
    Upload a batch of email dicts as JSON to MinIO raw bucket.
    Path: s3://bucket/raw/emails/YYYY-MM-DD/mailbox_type={type}/batch_{uuid}.json
    Returns the S3 key (path) written.
    """
    if not emails:
        raise ValueError("emails list cannot be empty")
    client = _client()
    key = f"raw/emails/{date}/mailbox_type={mailbox_type}/batch_{uuid.uuid4().hex}.json"
    body = json.dumps(emails, default=str)
    try:
        client.put_object(
            Bucket=BUCKET_RAW,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Uploaded %d emails to s3://%s/%s", len(emails), BUCKET_RAW, key)
        return f"s3://{BUCKET_RAW}/{key}"
    except ClientError as e:
        logger.exception("Failed to upload batch to %s: %s", key, e)
        raise


def download_parquet_partition(date: str, prefix: str = "analytics/daily") -> pd.DataFrame:
    """
    Download a single date partition of Parquet/JSON from MinIO and return as DataFrame.
    For analytics we store JSON; for raw Parquet use pyarrow/s3fs in Spark.
    Here we support reading JSON from processed bucket: processed/analytics/daily/YYYY-MM-DD.json
    """
    client = _client()
    key = f"{prefix}/{date}.json"
    try:
        resp = client.get_object(Bucket=BUCKET_PROCESSED, Key=key)
        data = json.loads(resp["Body"].read().decode("utf-8"))
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            return pd.DataFrame([data])
        return pd.DataFrame()
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.debug("No object at %s/%s", BUCKET_PROCESSED, key)
            return pd.DataFrame()
        logger.exception("Failed to download %s: %s", key, e)
        raise


def save_model_artifact(model_bytes: bytes, version: str) -> str:
    """
    Save model artifact to MinIO models bucket.
    Path: s3://bucket/models/v{version}/model (or model.pkl)
    Returns the S3 URI.
    """
    client = _client()
    key = f"models/v{version}/model.pkl"
    try:
        client.put_object(
            Bucket=BUCKET_MODELS,
            Key=key,
            Body=model_bytes,
            ContentType="application/octet-stream",
        )
        uri = f"s3://{BUCKET_MODELS}/{key}"
        logger.info("Saved model artifact to %s", uri)
        return uri
    except ClientError as e:
        logger.exception("Failed to save model to %s: %s", key, e)
        raise


def list_partitions(table: str) -> list[str]:
    """
    List partition paths (prefixes) for a given logical table in MinIO.
    Table can be 'emails_raw', 'emails_classified', 'analytics_daily'.
    Returns list of partition identifiers e.g. ['2026-01-15/faculty', '2026-01-15/personal'].
    """
    bucket = BUCKET_RAW if table == "emails_raw" else BUCKET_PROCESSED
    prefix_map = {
        "emails_raw": "raw/emails/",
        "emails_classified": "emails_classified/",
        "analytics_daily": "analytics/daily/",
    }
    prefix = prefix_map.get(table, "")
    client = _client()
    parts: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
            for prefix_obj in page.get("CommonPrefixes", []):
                p = prefix_obj.get("Prefix", "")
                if p and p != prefix:
                    parts.append(p.rstrip("/").replace(prefix.rstrip("/"), "").strip("/"))
            for prefix_obj in page.get("CommonPrefixes", []):
                p = prefix_obj.get("Prefix", "")
                if p:
                    # For nested partitions like raw/emails/2026-01-15/
                    rel = p[len(prefix) :].rstrip("/")
                    if rel and rel not in parts:
                        parts.append(rel)
    except ClientError as e:
        logger.warning("list_partitions failed for %s: %s", table, e)
    # Also list by keys for flat analytics_daily
    if table == "analytics_daily":
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                k = obj.get("Key", "")
                if k.endswith(".json"):
                    # e.g. analytics/daily/2026-01-15.json -> 2026-01-15
                    base = k.split("/")[-1].replace(".json", "")
                    if base and base not in parts:
                        parts.append(base)
    return sorted(set(parts))
