# RoleCraft API (Stage 1)

FastAPI + Neon Postgres (async SQLAlchemy 2.0) + Alembic + pgvector.

## Prerequisites

- **Python 3.11 or 3.12** (recommended — 3.14 may fail installing `pydantic-core` wheels)
- A [Neon](https://neon.tech) project (serverless Postgres). pgvector is available on all Neon plans; enable it per database with `CREATE EXTENSION` (also done in the first migration).
- (Optional) GCS bucket + `GEMINI_API_KEY` for real embeddings/uploads

## Setup

```bash
cd apps/api
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Paste your Neon pooled connection string into DATABASE_URL (see below)
```

### Database (Neon)

1. Create a project in the [Neon Console](https://console.neon.tech).
2. Open **Connect** and copy the **pooled** connection string (hostname contains `-pooler`, e.g. `ep-xxx-pooler.region.aws.neon.tech`). Pooled connections use PgBouncer and are preferred for Cloud Run / concurrent traffic.
3. Rewrite the scheme for async SQLAlchemy:

```
DATABASE_URL=postgresql+asyncpg://[user]:[password]@[ep-xxx-pooler.region.aws.neon.tech]/[dbname]?sslmode=require
```

Neon requires TLS. The app strips `sslmode` from the URL and passes `connect_args={"ssl": "require"}` because asyncpg does not use libpq's `sslmode` query param the same way as psycopg2. `pool_pre_ping=True` is set on the engine so scale-to-zero wakeups (~500ms) replace stale connections instead of failing hard.

pgvector (also applied by the first Alembic migration):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

You can run that in the Neon SQL Editor before the first migrate if you prefer.

### Migrations

```bash
alembic upgrade head
```

For heavy DDL, Neon recommends the **direct** (non-pooler) host; day-to-day app traffic should stay on the pooled URL.

### Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or: `bash run.sh` (Unix).

- Docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  

Local file uploads are stored under `apps/api/uploads/` and served at `/static/...` when `STORAGE_BACKEND=local`.

## Cloud Run deploy

No Cloud SQL instance, Auth Proxy, or Unix socket is required. Point `DATABASE_URL` at your Neon **pooled** connection string.

Prefer Secret Manager (avoids putting the URL in shell history / CI logs):

```bash
# One-time: store the Neon pooled URL
echo -n 'postgresql+asyncpg://USER:PASS@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require' \
  | gcloud secrets create DATABASE_URL --data-file=-

cd apps/api
gcloud run deploy rolecraft-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest" \
  --set-env-vars "JWT_SECRET=...,CORS_ORIGINS=https://your-frontend.example,STORAGE_BACKEND=gcs,GCS_BUCKET_NAME=..."
```

Or set the env var directly (less preferred):

```bash
gcloud run deploy rolecraft-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=postgresql+asyncpg://...,JWT_SECRET=...,CORS_ORIGINS=https://your-frontend.example,STORAGE_BACKEND=gcs,GCS_BUCKET_NAME=..."
```

GCS bucket setup and file storage remain unchanged — only the database host moved off Cloud SQL to Neon.

## Auth

`Authorization: Bearer <jwt>` on protected routes. Signup/signin return `{ access_token, user_id, role, plan }`.
