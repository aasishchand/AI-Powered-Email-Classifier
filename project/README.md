# Real-Time Email Classification Pipeline

## 1) Project Overview
This project upgrades a basic TF-IDF + sklearn email classifier into a modular, production-style data engineering pipeline. Emails are streamed through Kafka, classified in real time, persisted in PostgreSQL, corrected through a feedback API, and continuously improved via adaptive retraining.

## 2) Architecture Diagram
```text
Email Producer
    |
    v
Kafka Topic (email-stream)
    |
    v
Consumer -----> Model Service (TF-IDF + Logistic Regression)
    |
    v
PostgreSQL (emails + feedback)
    ^
    |
Feedback REST API (/feedback, /emails)
    |
    v
Adaptive Retraining (retraining/retrain.py)
    |
    v
Updated model.pkl + vectorizer.pkl
```

## 3) Prerequisites
- Python 3.9+
- Apache Kafka running locally or in Docker
- PostgreSQL running and reachable

## 4) Environment Setup
Create a `.env` file in the `project/` root:

```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=email-stream

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=email_pipeline
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword

MODEL_PATH=project/model/model.pkl
VECTORIZER_PATH=project/model/vectorizer.pkl

FEEDBACK_API_PORT=5000
```

## ▶️ How to Run (Local Kafka on Windows)

### Prerequisites
- Java 17+ installed
- Kafka 3.9.2 extracted to `C:\kafka`
- PostgreSQL running locally
- Python 3.9+

### 1) Create Kafka Topic (first time only)
Open Command Prompt:

```bat
cd C:\kafka
.\bin\windows\kafka-topics.bat --create --topic email-stream --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

### 2) Every Time You Work on This Project — Open 3 Terminals

**Terminal 1 — Zookeeper:**

```bat
cd C:\kafka
.\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties
```

**Terminal 2 — Kafka Broker:**

Kafka’s `kafka-server-start.bat` uses `wmic` only when heap size is not preset. On recent Windows builds `wmic` may be missing, which causes `'wmic' is not recognized`. Set heap options first so that path is skipped.

*Command Prompt:*

```bat
cd C:\kafka
set KAFKA_HEAP_OPTS=-Xmx1G -Xms1G
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

*PowerShell:*

```powershell
cd C:\kafka
$env:KAFKA_HEAP_OPTS = "-Xmx1G -Xms1G"
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

**Terminal 3–5 — Your project (real-time):** start the **consumer** first (it subscribes from `latest`), then the **API**, then the **producer** (continuous stream by default).

```bash
pip install -r project/requirements.txt
python -m project.utils.kafka_check
```

```bash
# Terminal A — classify & persist (runs until Ctrl+C)
python -m project.consumer.email_consumer
```

```bash
# Optional: standalone Flask API on port 5000 (same Postgres as below).
# The faculty dashboard uses FastAPI instead: sidebar **Live pipeline** → `/api/v1/pipeline/*`.
python -m project.api.feedback_api
```

```bash
# Terminal C — synthetic email stream (default: random sample every 2s)
python -m project.producer.email_producer
# One-off smoke batch: python -m project.producer.email_producer --once
```

Adaptive retraining (batch, on demand): `python -m project.retraining.retrain`

### 3) Send Feedback (curl or Postman)

```bash
curl -X POST http://localhost:5000/feedback \
  -H "Content-Type: application/json" \
  -d "{\"email_id\": \"abc-123\", \"correct_label\": \"not_spam\"}"
```

## 6) PostgreSQL Setup
Example setup in `psql`:

```sql
CREATE DATABASE email_pipeline;
CREATE USER email_user WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE email_pipeline TO email_user;
```

Then map credentials in `.env`:
- `POSTGRES_DB=email_pipeline`
- `POSTGRES_USER=email_user`
- `POSTGRES_PASSWORD=strong_password`

## 7) Extending the Pipeline
- Add more labels by collecting additional feedback and retraining regularly.
- Swap models by replacing `model/model_service.py` loading logic and retraining scripts.
- Scale consumers horizontally using different Kafka consumer group strategies.
- Add dashboarding by building a UI on top of `GET /emails`.
