# RoleCraft

AI-powered resume writing and job matching: Next.js frontend + FastAPI backend on Neon Postgres, with Groq-assisted resume/ATS/parse and vector-assisted fitment.

**Docs:** this file (setup & ops) · [`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md) (status & roadmap) · [`AGENTS.md`](AGENTS.md) (agent notes)

---

## Architecture

| Layer | Details |
|--------|---------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS v4, `UserContext` |
| **Backend** | FastAPI under `apps/api` — **Python 3.13** required |
| **Database** | Neon Postgres + pgvector (async SQLAlchemy 2.0, Alembic) |
| **Auth** | JWT; roles: candidate / company / admin |
| **AI** | Groq for resume generate / ATS / parse (deterministic fallback without key). Fitment rationale is still **template-based** — see Architecture Plan. |
| **Storage** | Local `apps/api/uploads/` or GCS |
| **Payments** | Mock (Stripe/Razorpay later) |

```
Browser → NEXT_PUBLIC_API_URL → apps/api routers → services → Neon
```

---

## Current status (Sep 2026)

| Area | Approx. |
|------|---------|
| Backend | ~95% |
| Frontend | ~90% |
| AI features | ~50% |
| Production readiness | ~40% |

**Done recently:** service-layer extraction, `ProfileItemService` CRUD, schema hardening, upload limits, CORS/IDOR/plan-limit fixes, API-backed candidate search, fitment rationale wiring, draft-job create fix, security pytest suite.

**Still open:** LLM fitment text, better embeddings, staging/CI/monitoring, real payments, analytics UI polish. Full checklist → [`ARCHITECTURE_PLAN.md`](ARCHITECTURE_PLAN.md).

---

## Prerequisites

- Node.js 18+ and npm  
- **Python 3.13** (use `apps/api/.venv313`)  
- Neon Postgres project  
- Optional: `GROQ_API_KEY`, GCS bucket  

---

## Frontend setup

```bash
# Repo root
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm install
npm run dev
```

---

## Backend setup

```bash
cd apps/api
python -m venv .venv313

# Windows
.\.venv313\Scripts\activate
# macOS/Linux: source .venv313/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Fill DATABASE_URL, JWT_SECRET, optional GROQ_API_KEY
alembic upgrade head
$env:PYTHONPATH="."   # Windows PowerShell; export PYTHONPATH=. on Unix
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  
- Uploads (local): `apps/api/uploads/` → `/static/...`

### Neon `DATABASE_URL`

1. Neon Console → **Connect** → **pooled** host (`-pooler` in hostname).  
2. Use async scheme:

```
DATABASE_URL=postgresql+asyncpg://USER:PASS@ep-xxx-pooler.region.aws.neon.tech/DB?sslmode=require
```

The app requires TLS (`connect_args` / `pool_pre_ping`). pgvector is enabled by the first migration (`CREATE EXTENSION vector`), or run `scripts/enable_pgvector.sql`.

Heavy DDL: prefer Neon’s **direct** (non-pooler) host; app traffic should stay on pooled.

### Groq (optional)

```
GROQ_API_KEY=gsk_...
# GROQ_MODEL=openai/gpt-oss-20b
# GROQ_ATS_MODEL=openai/gpt-oss-20b
```

Without a key, resume generation uses templates and ATS uses a hash-based score.

### Fitment rationale (interim)

Backend returns template strings such as `Strong skills overlap in {skills}.` — **not** LLM prose. The company candidates UI must show the API `rationale` field as-is.

### Admin user

```bash
cd apps/api
$env:PYTHONPATH="."
python scripts/make_admin.py you@email.com
```

### Auth

`Authorization: Bearer <jwt>` on protected routes. Signup/signin return `{ access_token, user_id, role, plan }`.

---

## Environment variables

**Frontend (`.env.local`):**

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

**Backend (`apps/api/.env`):**

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host/database?sslmode=require
JWT_SECRET=your-secret-key
GROQ_API_KEY=gsk_...                 # Optional
CORS_ORIGINS=http://localhost:3000
STORAGE_BACKEND=local                # or gcs
GCS_BUCKET_NAME=rolecraft-uploads    # if gcs
```

---

## Testing

```bash
# Backend (must be Python 3.13)
cd apps/api
$env:PYTHONPATH="."
python -m pytest tests/security tests/test_schema_validation.py -v

# Groq smoke (optional)
python scripts/groq_audit.py
```

Frontend: `npm test` / `npm run test:e2e` when configured.

---

## Local feature walkthrough

| Flow | Steps | Expected |
|------|--------|----------|
| Auth | Signup candidate + company | JWT stored, onboarding |
| Profile | Skills / education / experience | Persisted via `/candidates/me/*` |
| Resume AI | Generate / parse / PDF | Groq or deterministic fallback |
| Jobs | Company posts → candidate applies | Application row; draft jobs owner-only |
| Messages | Send via `/messages` | Thread both sides |
| Admin | `make_admin` → `/admin/dashboard` | Stats from `/admin/stats` |

---

## Deployment

### Backend (Cloud Run example)

```bash
# Prefer Secret Manager for DATABASE_URL / JWT_SECRET / GROQ_API_KEY
cd apps/api
gcloud run deploy rolecraft-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest,JWT_SECRET=JWT_SECRET:latest,GROQ_API_KEY=GROQ_API_KEY:latest" \
  --set-env-vars "CORS_ORIGINS=https://your-frontend.example,ENVIRONMENT=production,STORAGE_BACKEND=gcs,GCS_BUCKET_NAME=..."
```

Run `alembic upgrade head` against Neon before/at deploy. Alternatives: Railway, Render, Fly.io, ECS.

### Frontend (Vercel)

- Root = repo root; set `NEXT_PUBLIC_API_URL` to the API URL.

---

## Security notes

Upload validation lives in `apps/api/core/upload_limits.py` (MIME, magic bytes, size, path sanitization).

Deferred dependency CVEs (no clean upgrade path yet):

- `python-jose` / `ecdsa` / pinned `pyasn1`
- `weasyprint`, `starlette` (pinned by current FastAPI)

Monitor and upgrade when upstream allows.

---

## License / team

[Add license and team information here.]

## Acknowledgments

- [Next.js](https://nextjs.org/) · [FastAPI](https://fastapi.tiangolo.com/) · [Neon](https://neon.tech/) · [Groq](https://groq.com/)
