# Faculty Email Classification System

Enterprise-grade AI-powered email classification for university faculty: data ingestion, warehouse (Hive-style), Spark processing, ML (spam + topic), FastAPI backend, and React dashboard.

## Quick Start (Development)

### Backend (FastAPI)

1. Create virtualenv and install deps:
   ```bash
   cd email-api
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
2. Copy env and set DB:
   ```bash
   copy .env.example .env
   # Edit .env: DATABASE_URL=postgresql://admin:secret@localhost:5432/email_platform
   ```
3. Start PostgreSQL and Redis (e.g. Docker):
   ```bash
   docker run -d -p 5432:5432 -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=email_platform postgres:15-alpine
   docker run -d -p 6379:6379 redis:7-alpine
   ```
4. Create tables and seed users:
   ```bash
   # Run sql/init.sql on the DB (e.g. psql or GUI), then:
   python -m scripts.seed_users
   ```
5. Run API:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend (React + Vite + MUI)

1. Install and run:
   ```bash
   cd faculty-email-dashboard
   npm install
   npm run dev
   ```
2. Copy `.env.example` to `.env` and set `VITE_API_URL=http://localhost:8000/api/v1`.
3. Open http://localhost:5173. Login: `faculty@university.edu` / `faculty123` (after seeding).

### Full Stack with Docker

From repo root:

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000 (or via nginx on 80)
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

Seed users after first run (backend + postgres up):

```bash
docker-compose exec backend python -m scripts.seed_users
```

## Project Layout

- **email-api/** – FastAPI app: auth, dashboard metrics, emails list/detail, reclassify, WebSocket.
- **faculty-email-dashboard/** – React (Vite, MUI, Redux): dashboard, email table, analytics, settings.
- **sql/** – PostgreSQL init (users, feedback); Hive-style DDL in data-pipeline.
- **data-pipeline/** – Spark preprocessing script, Hive DDL, Airflow DAG stub for ETL/ML.
- **nginx/** – Reverse proxy config for Docker.

## Features

- **Dashboard**: KPIs (total emails, spam %, time saved), topic distribution, email volume and spam trends.
- **Emails**: Paginated list with filters, spam/ham chips, reclassify (feedback for retraining).
- **Analytics**: 30-day email volume trends.
- **Auth**: JWT login (form: username=email, password); optional Redis cache.
- **WebSocket**: Real-time metrics updates on dashboard (dev: simulated).

Backend uses mock/sample data when Spark/Hive are not available; replace with warehouse queries in production.

## Tech Stack

| Layer        | Tech                    |
|-------------|-------------------------|
| Frontend    | React 18, TypeScript, MUI, Redux, Recharts, Vite |
| Backend     | FastAPI, Pydantic, SQLAlchemy (async), PostgreSQL, Redis |
| Data/ML     | Spark (PySpark), Hive-style schema, Airflow DAG stub |

## License

Internal/university use.
