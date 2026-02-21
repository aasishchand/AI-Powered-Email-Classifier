# Big Data Architecture — AI-Powered-Email-Classifier

This document describes the big data extension of the Faculty Email Classifier: distributed storage, compute, orchestration, and scale-out ingestion.

---

## System Architecture (ASCII)

```
                    +------------------+
                    |   React Dashboard |
                    |   (port 3000)     |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |   Nginx :80       |
                    +--------+---------+
                             |
         +------------------+------------------+
         |                  |                  |
         v                  v                  v
+----------------+  +----------------+  +----------------+
| FastAPI :8000  |  | Airflow :8085  |  | Kafka UI :8080 |
| /api/v1/       |  | DAGs           |  | Topics/Lag     |
| /api/v1/bigdata|  +-------+--------+  +----------------+
+--------+-------+          |                   ^
         |                  |                   |
         |                  v                   |
         |          +----------------+          |
         |          | Spark Master  |          |
         |          | :7077, UI 8181|          |
         |          +-------+-------+          |
         |                  |                   |
         |         +--------+--------+         |
         |         v                 v         |
         |  +-------------+   +-------------+   |
         |  | Spark       |   | Spark       |   |
         |  | Worker 1    |   | Worker 2    |   |
         |  +-------------+   +-------------+   |
         |         |                 |           |
         v         v                 v           |
+----------------+         +----------------+   |
| MinIO :9000     |<--------+ Hive Metastore |   |
| (S3-compatible)|         | :9083          |   |
| buckets:       |         +----------------+   |
| emails-raw,    |                   ^           |
| emails-       |                   |           |
| processed,     |         +----------------+   |
| email-models   |         | Kafka :9092    |<--+
+----------------+         | (KRaft)        |
         ^                 +-------+--------+
         |                         |
         |                 +-------v--------+
         |                 | Kafka Consumer |
         |                 | (batch->MinIO) |
         +-----------------+ Kafka Producer |
                   (IMAP -> raw topic)     |
                           +---------------+
```

---

## Data Flow

1. **Ingestion**: IMAP fetcher (or existing Gmail sync) produces email messages to Kafka topic `emails-raw`. A batch consumer reads from Kafka and writes Parquet/JSON to MinIO `emails-raw/emails/ingestion_date=.../mailbox_type=.../`.
2. **Batch load**: Spark job `ingest_raw_emails.py` reads raw JSON from MinIO, validates schema, and writes to the Hive table `emails_raw` (Parquet).
3. **Classification**: Spark job `classify_emails.py` reads `emails_raw`, applies a classification UDF (spam/topic), and writes to `emails_classified`. A summary JSON is written to MinIO `processed/summaries/YYYY-MM-DD.json`.
4. **Analytics**: Spark job `compute_analytics.py` reads `emails_classified` over a 30-day window, aggregates daily metrics (volume, spam rate, topic distribution, top senders), and writes to `analytics_daily` and to MinIO `analytics/daily/YYYY-MM-DD.json`.
5. **API & UI**: FastAPI `/api/v1/bigdata/*` endpoints read from MinIO JSON (cached 5 min). The React "Big Data Analytics" page polls pipeline status, daily charts, model info, and storage partitions.

---

## Component Responsibilities

| Component        | Role |
|-----------------|------|
| MinIO           | S3-compatible object store for raw emails, processed Parquet/JSON, model artifacts. |
| Hive Metastore  | Catalog for Spark SQL tables (emails_raw, emails_classified, analytics_daily, model_registry). |
| Spark Master/Workers | Distributed compute for ingest, classify, analytics, and model training. |
| Kafka           | Message bus for scale-out ingestion; at-least-once consumer writes to MinIO. |
| Airflow         | Orchestrates DAGs: hourly ingestion pipeline, weekly model training, manual analytics backfill. |
| FastAPI bigdata | Serves analytics JSON from MinIO, pipeline status, model metadata, partition listing. |
| React BigDataAnalytics | Dashboard for pipeline status, volume chart, model panel, storage explorer, trigger controls. |

---

## Deployment (Docker Compose)

1. **Prerequisites**: Docker and Docker Compose. Copy `.env.bigdata` to `.env` and set credentials.
2. **Create Airflow and Hive DBs** (if using single Postgres):
   ```bash
   docker exec -it <postgres_container> psql -U admin -d email_platform -c "CREATE DATABASE airflow;"
   docker exec -it <postgres_container> psql -U admin -d email_platform -c "CREATE DATABASE hive_metastore;"
   ```
3. **Start order** (Compose handles dependencies; for manual order):
   - `postgres`, `redis`, `minio` (wait for healthy)
   - `minio-init` (one-shot buckets)
   - `spark-master`, `spark-worker-1`, `spark-worker-2`
   - `hive-metastore`, `kafka`, `kafka-ui`
   - `airflow-init` (one-shot), then `airflow-webserver`, `airflow-scheduler`, `airflow-worker`
   - `backend`, `frontend`, `nginx`
4. **Full stack**:
   ```bash
   docker compose --env-file .env up -d
   ```

---

## Configuration Reference (Env Vars)

| Variable | Description |
|---------|-------------|
| MINIO_ROOT_USER, MINIO_ROOT_PASSWORD | MinIO credentials. |
| MINIO_BUCKET_RAW, MINIO_BUCKET_PROCESSED, MINIO_BUCKET_MODELS | Bucket names. |
| SPARK_MASTER_URL | e.g. `spark://spark-master:7077`. |
| HIVE_METASTORE_URI | e.g. `thrift://hive-metastore:9083`. |
| KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_EMAILS_RAW, KAFKA_TOPIC_EMAILS_CLASSIFIED | Kafka config. |
| AIRFLOW_UID, AIRFLOW_ADMIN_USER, AIRFLOW_ADMIN_PASSWORD | Airflow admin. |
| POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB | PostgreSQL (app + optional Airflow/Hive DBs). |
| BACKEND_URL | Used by Airflow to call `/api/v1/bigdata/analytics/refresh`. |

---

## Backfilling Historical Data

1. Place raw email JSON under MinIO `emails-raw/raw/emails/YYYY-MM-DD/mailbox_type=faculty/` (or use Kafka producer + consumer to backfill).
2. Run Spark ingest for each date:
   ```bash
   ./data-pipeline/spark/submit.sh ingest_raw_emails --date 2026-01-15 --mailbox-type faculty
   ```
3. Run classify and analytics:
   ```bash
   ./data-pipeline/spark/submit.sh classify_emails --date 2026-01-15
   ./data-pipeline/spark/submit.sh compute_analytics --end-date 2026-01-20 --days 30
   ```
4. Or trigger the Airflow DAG `analytics_backfill` with config `{"end_date": "2026-01-20", "days": 7}`.

---

## Promoting a New Model to Production

1. Train via Airflow DAG `model_training_pipeline` or manually:
   ```bash
   ./data-pipeline/spark/submit.sh train_model --version 20260131
   ```
2. The job writes the model to MinIO `email-models/models/v{version}/` and appends a row to `model_registry` (Parquet).
3. To set the champion: update the `model_registry` table so that the new version has `is_champion=true` and others `false`. The FastAPI `/bigdata/model/current` endpoint can be extended to read the champion from this table or a JSON manifest in MinIO.

---

## Monitoring and Observability

| System | URL / How |
|--------|----------|
| Spark Master UI | http://localhost:8181 |
| Airflow UI | http://localhost:8085 (admin / admin) |
| Kafka UI | http://localhost:8080 |
| MinIO Console | http://localhost:9001 |
| FastAPI health | http://localhost:8000/health |
| Big Data dashboard | React app → Big Data Analytics (sidebar). |

Logs: use structured logging (JSON) in producer/consumer and Spark jobs; Airflow task logs are in the Airflow UI.
