# Multi-stage Dockerfile for ingestion service (Kafka producer + consumer)
FROM python:3.11-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

FROM base AS producer
COPY data-pipeline/ingestion/ /app/
COPY data-pipeline/storage/ /app/storage/
RUN pip install --no-cache-dir confluent-kafka boto3 prometheus_client
ENV PYTHONPATH=/app
CMD ["python", "-m", "kafka_producer"]

FROM base AS consumer
COPY data-pipeline/ingestion/ /app/
COPY data-pipeline/storage/ /app/storage/
RUN pip install --no-cache-dir confluent-kafka boto3 pyarrow
ENV PYTHONPATH=/app
CMD ["python", "-m", "kafka_consumer"]
