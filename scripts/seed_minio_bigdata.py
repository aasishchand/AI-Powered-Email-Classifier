"""
Upload sample analytics JSON into MinIO so the dashboard "Big Data Analytics" charts have data.

Prerequisites:
  - MinIO listening on http://localhost:9000 (default dev creds minioadmin/minioadmin).
  - pip install boto3

Usage (from repo root):
  python scripts/seed_minio_bigdata.py

Env overrides (optional):
  MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_BUCKET_PROCESSED
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def main() -> None:
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    access = os.environ.get("MINIO_ACCESS_KEY", os.environ.get("MINIO_ROOT_USER", "minioadmin"))
    secret = os.environ.get("MINIO_SECRET_KEY", os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"))
    bucket = os.environ.get("MINIO_BUCKET_PROCESSED", "emails-processed")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)

    today = datetime.now(timezone.utc).date()
    for i in range(30):
        day = today - timedelta(days=i)
        date_str = day.isoformat()
        payload = {
            "metric_date": date_str,
            "daily_volume": 80 + (i * 3) % 120,
            "spam_count": 5 + (i * 2) % 35,
            "spam_rate": round(0.05 + (i % 10) * 0.02, 3),
            "ham_count": 75 + (i * 5) % 90,
            "topic_distribution": {
                "general": 20 + i % 15,
                "academic": 15 + i % 20,
                "administrative": 10 + i % 12,
                "research": 8 + i % 10,
            },
        }
        key = f"analytics/daily/{date_str}.json"
        body = json.dumps(payload, indent=2).encode("utf-8")
        client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
        print(f"Put s3://{bucket}/{key} ({len(body)} bytes)")


if __name__ == "__main__":
    main()
