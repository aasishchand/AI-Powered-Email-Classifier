"""Big Data API: read from MinIO analytics JSON; pipeline status; model registry; storage partitions."""
import json
import logging
import os
import time
from typing import Any, Callable

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory TTL cache: key -> (value, expiry_ts)
_cache: dict[str, tuple[Any, float]] = {}
TTL_SEC = 300  # 5 minutes


def _cached(key: str, fetcher: Callable[[], Any]) -> Any:
    now = time.monotonic()
    if key in _cache:
        val, expiry = _cache[key]
        if now < expiry:
            return val
    val = fetcher()
    _cache[key] = (val, now + TTL_SEC)
    return val


def _s3_client_sync():
    import boto3
    from botocore.config import Config
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    access = os.environ.get("MINIO_ACCESS_KEY", os.environ.get("MINIO_ROOT_USER", "minioadmin"))
    secret = os.environ.get("MINIO_SECRET_KEY", os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"))
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _read_json_from_s3(bucket: str, key: str) -> dict | list | None:
    try:
        client = _s3_client_sync()
        resp = client.get_object(Bucket=bucket, Key=key)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except Exception as e:
        if hasattr(e, "response") and getattr(e.response, "Error", None):
            if e.response["Error"].get("Code") == "NoSuchKey":
                return None
        logger.debug("S3 read %s/%s: %s", bucket, key, e)
        return None


def _list_objects(bucket: str, prefix: str) -> list[str]:
    try:
        client = _s3_client_sync()
        paginator = client.get_paginator("list_objects_v2")
        out = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                k = obj.get("Key", "")
                if k:
                    out.append(k)
        return out
    except Exception as e:
        logger.warning("list_objects %s/%s: %s", bucket, prefix, e)
        return []


bucket_processed = os.environ.get("MINIO_BUCKET_PROCESSED", "emails-processed")
bucket_models = os.environ.get("MINIO_BUCKET_MODELS", "email-models")
bucket_raw = os.environ.get("MINIO_BUCKET_RAW", "emails-raw")


@router.get("/analytics/daily")
async def get_analytics_daily(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
):
    """Read daily analytics from MinIO JSON (cached 5 min)."""
    def fetcher():
        items = []
        prefix = "analytics/daily/"
        keys = _list_objects(bucket_processed, prefix)
        for k in keys:
            if not k.endswith(".json"):
                continue
            date_part = k.replace(prefix, "").replace(".json", "")
            if start_date <= date_part <= end_date:
                data = _read_json_from_s3(bucket_processed, k)
                if data:
                    items.append(data if isinstance(data, dict) else {"metric_date": date_part, "data": data})
        return sorted(items, key=lambda x: x.get("metric_date", ""))

    try:
        data = _cached(f"analytics_daily:{start_date}:{end_date}", fetcher)
        return {"data": data}
    except Exception as e:
        logger.exception("analytics/daily: %s", e)
        return JSONResponse(status_code=502, content={"detail": str(e)})


@router.get("/analytics/topics")
async def get_analytics_topics(date: str = Query(..., description="Date YYYY-MM-DD")):
    """Topic distribution for a date from MinIO."""
    def fetcher():
        data = _read_json_from_s3(bucket_processed, f"analytics/daily/{date}.json")
        if not data:
            return {}
        return data.get("topic_distribution", {})

    try:
        data = _cached(f"topics:{date}", fetcher)
        return {"date": date, "topic_distribution": data}
    except Exception as e:
        logger.exception("analytics/topics: %s", e)
        return JSONResponse(status_code=502, content={"detail": str(e)})


@router.get("/analytics/spam-trend")
async def get_spam_trend(days: int = Query(30, ge=1, le=90)):
    """Spam rate time series for the last N days."""
    from datetime import datetime, timedelta
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    start_date = start.strftime("%Y-%m-%d")
    end_date = end.strftime("%Y-%m-%d")

    def fetcher():
        items = []
        prefix = "analytics/daily/"
        keys = _list_objects(bucket_processed, prefix)
        for k in keys:
            if not k.endswith(".json"):
                continue
            date_part = k.replace(prefix, "").replace(".json", "")
            if start_date <= date_part <= end_date:
                data = _read_json_from_s3(bucket_processed, k)
                if data and isinstance(data, dict):
                    items.append({
                        "date": date_part,
                        "spam_rate": data.get("spam_rate", 0),
                        "daily_volume": data.get("daily_volume", 0),
                        "spam_count": data.get("spam_count", 0),
                    })
        return sorted(items, key=lambda x: x["date"])

    try:
        data = _cached(f"spam_trend:{days}", fetcher)
        return {"series": data}
    except Exception as e:
        logger.exception("analytics/spam-trend: %s", e)
        return JSONResponse(status_code=502, content={"detail": str(e)})


@router.get("/model/current")
async def get_model_current():
    """Current champion model metadata from MinIO / Hive (stub: read from registry JSON if present)."""
    def fetcher():
        # Try to read a registry manifest or first parquet metadata
        keys = _list_objects(bucket_models, "model_registry/")
        if not keys:
            return {"version": None, "training_date": None, "accuracy": None, "f1": None}
        # Simplified: no JSON manifest; return placeholder
        return {"version": "latest", "training_date": None, "accuracy": None, "f1": None}

    try:
        data = _cached("model_current", fetcher)
        return data
    except Exception as e:
        logger.exception("model/current: %s", e)
        return JSONResponse(status_code=502, content={"detail": str(e)})


@router.get("/model/history")
async def get_model_history():
    """All model versions + metrics (stub)."""
    def fetcher():
        return []
    try:
        data = _cached("model_history", fetcher)
        return {"versions": data}
    except Exception as e:
        logger.exception("model/history: %s", e)
        return JSONResponse(status_code=502, content={"detail": str(e)})


@router.post("/analytics/refresh")
async def post_analytics_refresh():
    """Trigger refresh (e.g. call Airflow DAG or recompute). Idempotent."""
    return {"status": "ok", "message": "Refresh triggered"}


@router.get("/pipeline/status")
async def get_pipeline_status():
    """Airflow DAG run statuses (stub: would call Airflow REST API)."""
    airflow_url = os.environ.get("AIRFLOW_WEBSERVER_URL", "http://airflow-webserver:8085")
    def fetcher():
        try:
            import urllib.request
            req = urllib.request.Request(f"{airflow_url}/api/v1/dags/email_ingestion_pipeline/dagRuns?limit=5")
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode("utf-8"))
                return data.get("dag_runs", [])
        except Exception as e:
            logger.debug("Airflow status: %s", e)
            return []

    try:
        runs = _cached("pipeline_status", fetcher)
        return {"dag_runs": runs}
    except Exception as e:
        logger.exception("pipeline/status: %s", e)
        return {"dag_runs": []}


@router.get("/storage/partitions")
async def get_storage_partitions(
    table: str = Query("emails_raw", description="emails_raw | emails_classified | analytics_daily"),
):
    """List available data partitions in MinIO."""
    prefix_map = {
        "emails_raw": "raw/emails/",
        "emails_classified": "emails_classified/",
        "analytics_daily": "analytics/daily/",
    }
    prefix = prefix_map.get(table, "raw/emails/")
    bucket = bucket_raw if table == "emails_raw" else bucket_processed

    def fetcher():
        keys = _list_objects(bucket, prefix)
        parts = set()
        for k in keys:
            if k.endswith(".json"):
                parts.add(k.replace(prefix, "").replace(".json", ""))
            else:
                # partition path like 2026-01-15/faculty
                rest = k.replace(prefix, "").rstrip("/")
                if rest:
                    parts.add(rest)
        return sorted(parts)

    try:
        data = _cached(f"partitions:{table}", fetcher)
        return {"table": table, "partitions": data}
    except Exception as e:
        logger.exception("storage/partitions: %s", e)
        return JSONResponse(status_code=502, content={"detail": str(e)})
