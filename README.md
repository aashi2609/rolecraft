# RoleCraft

RoleCraft is an AI-powered talent acquisition and career management platform that connects candidates and companies with intelligent matching, ATS resume scoring, pgvector semantic search, verified candidate-to-recruiter messaging, and subscription management.

Built as a modern monorepo with a **FastAPI** backend (Python 3.11.9) and a **Next.js 16 / React 19** frontend.

---

## Architecture Overview

```
rolecraft/
├── app/                            # Next.js App Router (Frontend)
│   ├── (admin)/                    # Admin portal routes
│   ├── (candidate)/                # Candidate portal routes
│   ├── (company)/                  # Company / Recruiter routes
│   ├── (public)/                   # Landing, pricing, public job views
│   ├── signin/ signup/ ...         # Authentication pages
│   └── layout.tsx                  # Root layout & providers
├── components/                     # Reusable UI components (Radix, Tailwind)
├── context/                        # React context (UserContext, auth state)
├── hooks/                          # Custom React hooks
├── lib/                            # API client, TypeScript definitions, utils
├── apps/api/                       # FastAPI Backend
│   ├── alembic/                    # Database migrations (23 revisions to head)
│   ├── core/                       # Auth, DB engine, security, rate limit, guards
│   ├── models/                     # SQLAlchemy 2.0 declarative models
│   ├── routers/                    # FastAPI route handlers
│   ├── schemas/                    # Pydantic v2 validation models
│   ├── scripts/                    # Maintenance & data reconciliation scripts
│   ├── services/                   # Business logic layer
│   └── tests/                      # Pytest suite (327 tests)
└── .github/workflows/ci.yml        # Unified CI pipeline (Python 3.11.9, PG 18)
```

---

## Tech Stack

### Frontend
- **Framework**: Next.js 16 (App Router), React 19, TypeScript
- **Styling**: Tailwind CSS v4, Lucide Icons, Framer Motion
- **Components**: Radix UI Primitives, cmdk, Recharts

### Backend
- **Framework**: FastAPI (ASGI), Pydantic v2, Pydantic-Settings
- **Runtime**: Python 3.11.9 (pinned in `runtime.txt` and CI)
- **ORM / Database**: SQLAlchemy 2.0 (asyncio + asyncpg), Alembic migrations
- **Database Engine**: PostgreSQL with `pgvector` (hosted on Neon Serverless with connection pooling)
- **Authentication**: JWT (python-jose, bcrypt), role-based access (`candidate`, `company`, `admin`)
- **Rate Limiting**: SlowAPI with in-memory / Redis backend

### AI & Search
- **Embeddings**: OpenAI-compatible `text-embedding-3-small` (1536 dimensions) stored in pgvector
- **LLM Engine**: Groq (`openai/gpt-oss-20b`) for ATS fitment scoring, resume generation, JD parsing, and match rationales
- **Fallbacks**: Deterministic template fallbacks if AI provider is unreachable or unconfigured

### Payments & Storage
- **Payments**: Razorpay with HMAC-SHA256 webhook signature verification and idempotency protection
- **File Storage**: Local filesystem (`uploads/`) with magic-byte MIME validation or Google Cloud Storage (GCS)

---

## Core Features

### 1. Candidate Portal
- **Profile Management**: Multi-step profile builder covering education, certifications, employment history, projects, and skills.
- **AI Resume Builder & ATS Scoring**: Target-vertical resume generation with real-time ATS match scoring and breakdown against job descriptions.
- **Job Discovery & Fitment**: Semantic vector matching with fitment percentage and AI-generated fitment rationales.
- **Application Tracking**: Real-time status tracking (`applied`, `shortlisted`, `interview`, `rejected`).
- **Direct Messaging**: In-app conversation threads with recruiters with unread counters and notification badges.

### 2. Company / Recruiter Portal
- **Job Posting Lifecycle**: Create, publish, update, and manage job requisitions (`draft`, `live`, `closed`).
- **Applicant Tracking System (ATS)**: Review applicant pipelines with candidate fitment scores and resume previews.
- **Gated Resume Access**: Centralized security gating (`can_company_view_resume`) ensuring recruiters can only access resumes submitted for their specific job postings (with 60/hr rate limit and access audit logs).
- **Candidate Search**: Semantic search over candidate pool with experience, salary, and location filters.
- **Recruiter Inbox**: Company inbox with O(1) query-optimized thread batching, PII protection, and policy gating.

### 3. Admin & Platform Operations
- **User & Subscription Management**: Plan tier overrides, grant activations, and renewal tracking.
- **Subscription Invariant**: Partial unique index enforcing a single active or pending subscription per user.
- **Audit Trails**: Detailed logs for subscription changes, payments, and privileged data access.
- **System Analytics**: Platform-wide metrics, candidate/company activity trends, and application pipeline health.

---

## Getting Started

### Prerequisites
- **Node.js**: `>= 20.19.0`
- **npm**: `>= 10.0.0`
- **Python**: `3.11.9`
- **PostgreSQL**: With `pgvector` extension enabled (or a Neon database instance)

---

### Backend Setup (`apps/api`)

1. **Navigate to the API directory**:
   ```bash
   cd apps/api
   ```

2. **Create and activate a Python 3.11.9 virtual environment**:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   Fill in your database URL, JWT secret, and API keys:
   - `DATABASE_URL`: `postgresql+asyncpg://user:pass@host/dbname?sslmode=require`
   - `TEST_DATABASE_URL`: Isolated test database for running pytest
   - `JWT_SECRET`: Random 64-character secret
   - `GROQ_API_KEY`: Groq API key for LLM operations (optional in dev)
   - `EMBEDDING_API_KEY`: API key for vector embeddings (optional in dev)
   - `PAYMENTS_MODE`: `disabled`, `test`, or `live`

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the development server**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   The API will be available at `http://localhost:8000`. Swagger documentation is accessible at `http://localhost:8000/docs` in development mode.

---

### Frontend Setup

1. **Install dependencies from the repository root**:
   ```bash
   npm install
   ```

2. **Configure environment variables**:
   Create `.env.local` in the root directory:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` in your browser.

---

## Database Migrations

Migrations are managed with **Alembic**. The schema includes 23 migration revisions up to head revision `p8q9r0s1t2u3`.

- **Apply all migrations**:
  ```bash
  cd apps/api
  alembic upgrade head
  ```
- **Inspect current revision**:
  ```bash
  alembic current
  ```
- **Create a new migration**:
  ```bash
  alembic revision --autogenerate -m "description_of_change"
  ```

> **Database Safety Guard**: The backend includes `core/db_guard.py` which prevents automated test suites or rehearsal migrations from ever executing against the primary production database.

---

## Testing & Quality Assurance

### Running Backend Tests
Tests run exclusively against `TEST_DATABASE_URL` with transaction rollback isolation per test:
```bash
cd apps/api
pytest tests/ -v
```

**Test Suite Coverage**:
- `327` tests collected, `0` skipped, `0` failed
- Full route verification for authentication, RBAC, IDOR protection, and rate limiting
- Eager-loading regression tests preventing SQLAlchemy `MissingGreenlet` errors (`test_job_lazy_load.py`)
- O(1) query count assertions for batch messaging endpoints (`test_messages.py`)
- Subscription partial unique index invariant tests (`test_subscription_invariant.py`)
- Gated resume viewing and PDF streaming header security (`test_step_c_resume_access.py`)

### Linting & Formatting
```bash
# Backend (Python / Ruff)
cd apps/api
ruff check .
ruff format --check .

# Frontend (TypeScript / ESLint)
npm run lint
npm run typecheck
```

### Continuous Integration (CI)
The project runs a strict GitHub Actions workflow (`.github/workflows/ci.yml`) on all PRs and pushes to `main`:
- **OS**: Ubuntu 24.04 with Dockerized `pgvector/pgvector:pg18`
- **Python**: Asserted exact match `Python 3.11.9`
- **Shell**: Declarative `set -euo pipefail`
- **Checks**: Pip security audit (`pip-audit`), Ruff lint/format, Alembic migration verification, full Pytest execution with JUnit skip-gate, Next.js build, and TypeScript typechecking.

---

## API Routes Summary

| Prefix | Description | Auth Required |
|---|---|---|
| `/auth` | Sign up, sign in, token refresh, password reset, account deletion | Public / Bearer |
| `/jobs` | Job postings CRUD, status transitions, search, and filters | Public / Role-gated |
| `/candidates` | Candidate profile CRUD (education, experience, skills, projects) | Candidate |
| `/companies` | Company profiles and recruiter settings | Company |
| `/applications` | Job applications submit, status pipeline updates, candidate list | Candidate / Company |
| `/messages` | Thread batch listing, messaging, reply, unread counts | Candidate / Company |
| `/resumes` | Resume generation, PDF download, ATS fitment scoring | Candidate |
| `/payments` | Razorpay order creation, payment verification, webhook ingestion | Role-gated / Webhook HMAC |
| `/admin` | Subscription grants, audit logs, user management, metrics | Admin |
| `/analytics` | Recruiter and candidate pipeline analytics and performance | Role-gated |
| `/files` | Authenticated file serving with MIME verification | Role-gated |

---

## Maintenance Scripts (`apps/api/scripts/`)

- `backfill_embeddings.py`: Generates and backfills 1536-dimensional vector embeddings for existing job postings and candidate profiles.
- `subscription_reconciliation.py`: Audits and reconciles subscription states, cancelling duplicates and logging inconsistencies.
- `make_admin.py`: CLI utility to grant administrative privileges to a user account.
- `backup_db.py` / `restore_db.py`: Database backup and restoration automation.

---

## Deployment

The backend is configured for deployment on **Render** via `render.yaml`:
- **Runtime**: Python 3.11.9
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

The frontend is deployable to **Vercel** or any Node.js hosting platform with zero configuration.

---

## License

Private and proprietary. All rights reserved.
