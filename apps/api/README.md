# RoleCraft API (Stage 1)

FastAPI + Neon Postgres (async SQLAlchemy 2.0) + Alembic + pgvector.

## Prerequisites

- **Python 3.11 or 3.12** (recommended — 3.14 may fail installing `pydantic-core` wheels)
- A [Neon](https://neon.tech) project (serverless Postgres). pgvector is available on all Neon plans; enable it per database with `CREATE EXTENSION` (also done in the first migration).
- (Optional) GCS bucket for uploads
- (Optional) `GROQ_API_KEY` for AI resume generation, ATS scoring, and PDF parsing

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

### Groq (AI resume generation)

1. Create an API key at [console.groq.com](https://console.groq.com).
2. Add to `apps/api/.env`:

```
GROQ_API_KEY=gsk_...
# Optional model overrides (default: openai/gpt-oss-20b)
# GROQ_MODEL=openai/gpt-oss-20b
# GROQ_ATS_MODEL=openai/gpt-oss-20b
```

3. Restart uvicorn. Resume generation, ATS scoring, and `POST /resumes/parse` use Groq. Without a key, resume generation falls back to deterministic templates and ATS uses a hash-based score.

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



Local Testing Guide (Full Feature Walkthrough)
1. Prerequisites
# Terminal 1 — API
cd apps/api
python -m venv .venv313
.venv313\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env               # fill DATABASE_URL, JWT_SECRET, GROQ_API_KEY
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Terminal 2 — Frontend
cd c:\rolecraft
cp .env.local.example .env.local     # or create:
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm install
npm run dev
2. Create admin user
cd apps/api
python make_admin.py your@email.com
3. Test matrix
Flow	Steps	Expected
Auth
Signup candidate + company at /signup
JWT stored, redirect to onboarding
Candidate onboarding
Complete profile steps, save skills/education
Data in Neon via /candidates/me
Resume AI
Onboarding → generate resume
Groq-powered content with your name (check API logs for "AI-powered")
Jobs
Company posts job → candidate browses /jobs → apply
Application created
Messages
Company/candidate send via /messages
Thread appears both sides
Settings
Change password, notification prefs
API updates
Admin
Sign in as admin → /admin/dashboard
Stats load from /admin/stats
ATS/PDF
Regenerate resume, download PDF
Score + PDF download
Parse
Upload PDF in onboarding
Returns structured JSON (needs Groq key)
4. Verify Groq is active
cd apps/api
$env:PYTHONPATH="."; python scripts/groq_audit.py
Look for status: OK on resume, ATS, and parse tests.

5. API docs
Open http://127.0.0.1:8000/docs for interactive testing.

Hosting Frontend & Backend Separately
Backend (FastAPI) — e.g. Google Cloud Run
cd apps/api
# Set secrets in Cloud Run / Neon console:
# DATABASE_URL=postgresql+asyncpg://...@ep-xxx-pooler.neon.tech/neondb?sslmode=require
# JWT_SECRET=<64-char random>
# GROQ_API_KEY=gsk_...
# CORS_ORIGINS=https://your-frontend.vercel.app
# STORAGE_BACKEND=gcs
# GCS_BUCKET_NAME=rolecraft-uploads
gcloud run deploy rolecraft-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest,JWT_SECRET=JWT_SECRET:latest,GROQ_API_KEY=GROQ_API_KEY:latest" \
  --set-env-vars "CORS_ORIGINS=https://your-frontend.vercel.app,ENVIRONMENT=production,STORAGE_BACKEND=gcs"
Run migrations against Neon before deploy:

alembic upgrade head
Before production: Remove allow_origin_regex=".*" from main.py.

Frontend (Next.js) — e.g. Vercel
Push repo to GitHub
Import project in Vercel (root directory = repo root)
Set environment variable:
NEXT_PUBLIC_API_URL=https://rolecraft-api-xxxxx.run.app
Deploy — Vercel builds next build automatically
Alternative stacks
Backend	Frontend
Railway / Render / Fly.io
Vercel / Netlify / Cloudflare Pages
AWS ECS + ALB
S3 + CloudFront (static export)