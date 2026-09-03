# RoleCraft Architecture & Implementation Plan

> **Last updated:** September 2026 (post security + structural pass)  
> **Canonical docs:** this file (roadmap) + root [`README.md`](README.md) (setup & ops). There is no separate `apps/api/README.md`.

---

## 1. Architecture overview

```
rolecraft/                          # Next.js 16 frontend (App Router)
├── app/                            # Routes: (candidate) | (company) | (admin) | public
├── components/ context/ hooks/ lib/
└── apps/api/                       # FastAPI backend
    ├── routers/                    # Thin HTTP layer
    ├── services/                   # Business logic
    ├── core/                       # Auth, DB, uploads, websockets
    ├── models/ schemas/ alembic/
    ├── tests/                      # pytest (Python 3.13)
    └── scripts/                    # make_admin, groq_audit, enable_pgvector
```

| Layer | Stack |
|--------|--------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4, `UserContext` |
| Backend | FastAPI, **Python 3.13**, async SQLAlchemy 2.0 |
| DB | Neon Postgres + pgvector |
| Auth | JWT (python-jose, bcrypt); roles: candidate / company / admin |
| AI | **Groq** for resume generate / ATS / PDF parse; deterministic fallbacks without key |
| Fitment | OpenAI-compatible embeddings (`EMBEDDING_API_KEY`) + Groq LLM rationales (template fallback) |
| Storage | Local `uploads/` or GCS |
| Payments | Mock (Stripe/Razorpay later) |

**Request path:** Browser → `NEXT_PUBLIC_API_URL` → FastAPI `routers/*` → `services/*` → Neon.

**Naming boundary:** API/DB use `snake_case` (`job_role`); frontend uses camelCase (`jobRole`) via mappers in `UserContext` / job pages.

---

## 2. Current completion

| Area | Status | Notes |
|------|--------|--------|
| Backend product APIs | **~95%** | CRUD, search, applications, messages, admin, analytics router |
| Frontend product UI | **~92%** | Full role flows; analytics dashboard wired with export |
| AI features | **~75%** | Groq for resume/ATS/parse + rationales; OpenAI-compatible embeddings when keyed |
| Production readiness | **~45%** | Security tests + staging CI workflow; deploy/monitoring open |

---

## 3. Done (including recent structural/security pass)

### Backend
- [x] Auth: signup / signin / forgot-password / change-password; password complexity in Pydantic (min 8, letter + digit); role as `Literal`
- [x] Plans & subscription gates (`check_plan_limit` for resumes / job postings)
- [x] Candidate profile CRUD via shared **`ProfileItemService`** (education, certifications, experience, projects)
- [x] Company + job CRUD; draft jobs IDOR-safe (owner only); `matched` / `shortlisted` from `applications`
- [x] Applications, messages, notifications, uploads (MIME / magic bytes / size / path sanitization)
- [x] **Services extracted from fat routers:** `candidate_search_service`, `job_search_service`, `resume_service`, `pdf_service`, `subscription_service`, `admin_service`, `fitment_service`, `profile_item_service`
- [x] Schema tightening: salaries `ge=0` + max≥min; experience dates; job/application status Literals; JobOut enum coerce (fixed POST `/jobs` 500)
- [x] `job_role` / `job_level` persisted correctly (company form no longer sends bare `role` / `level`)
- [x] Fitment rationale via `fitment_rationale_service` (Groq + template fallback); `rationale_source` on API + company UI
- [x] `embedding_service` — refresh job/resume vectors on profile and job updates
- [x] Server-side job filters wired in candidate jobs page; company candidate `locations` → API `location`
- [x] Tests: `tests/test_fitment_rationale_service.py`; CI workflow `.github/workflows/ci.yml`
- [x] OpenAI-compatible embeddings via `embedding_client` (`EMBEDDING_API_KEY`; mock fallback)
- [x] Analytics — `analytics_service` with 60s cache, typed schemas, CSV export + refresh in UI
- [x] `job_type` filter on `GET /jobs` (remote/hybrid/onsite)

### Frontend
- [x] Candidate / company / admin App Router flows
- [x] Company candidate search → `GET /candidates/search` (SEED only as offline fallback)
- [x] Job list/detail mappers include `jobRole` / `jobLevel`
- [x] Plan gating, pricing/checkout (mock pay), settings subscriptions
- [x] Fitment modal: API rationale + LLM vs template note via `rationaleSource`
- [x] Candidate / company analytics dashboards wired to `/analytics` with export

### Ops / tooling
- [x] Neon + Alembic migrations; `scripts/enable_pgvector.sql`
- [x] `scripts/make_admin.py`, `scripts/groq_audit.py`
- [x] Cloud Run–oriented deploy notes (in root README)

---

## 4. Left to do

### High priority
- [ ] **Staging deploy** — Cloud Run + Vercel (or equivalent) with secrets, CORS locked down

### Medium priority
- [ ] AI double-check shortlist (LLM validation of top fitment hits)
- [ ] Real payments (Stripe/Razorpay) + webhooks + cancel/pause/resume
- [ ] Bulk company actions; export; saved searches / search history
- [ ] Rate limiting; broader integration/E2E test coverage

### Lower priority
- [ ] External job ingestion (LinkedIn/Indeed, etc.)
- [ ] APM / Sentry / structured logging / AI cost alerts
- [ ] Accessibility & SEO polish; CDN; backup policy
- [ ] Replace `python-jose` when a maintained JWT stack is chosen (known transitive CVEs)

---

## 5. Service / router map (current)

| Router | Primary services / notes |
|--------|---------------------------|
| `auth` | Core security; Pydantic signup/password rules |
| `candidates` | `ProfileItemService`, `candidate_search_service`, `embedding_service` (profile sync) |
| `jobs` | `job_search_service`, `fitment_service`, `embedding_service` (job sync) |
| `resumes` | `resume_service`, `pdf_service`, Groq via `ai_client` |
| `applications` | Auto-resume via `get_or_generate_resume` |
| `notifications` (+ uploads/subscriptions) | `storage_service`, `subscription_service`, `upload_limits` |
| `admin` | `admin_service` |
| `messages` / `analytics` / `companies` | `analytics_service` (cached aggregates), domain routers |

---

## 6. Phased roadmap (remaining work only)

### Phase A — AI fitment honesty → quality
1. ~~Keep template rationale until LLM path ships~~ — LLM path live behind `FITMENT_LLM_RATIONALES`.
2. ~~Add Groq rationale generation~~ — `fitment_rationale_service`; candidate search stays template-only.
3. ~~Invalidate embeddings on profile/resume change~~ — `embedding_service` hooks on profile CRUD + job create/update.
4. Swap mock embeddings for a real provider when chosen. → **Done:** `EMBEDDING_API_KEY` + OpenAI-compatible API; mock fallback retained.

### Phase B — Payments & subscriptions
1. Provider SDK + webhooks.
2. Cancel / pause / resume + audit log.
3. Invoices (optional PDF).

### Phase C — Production
1. ~~Staging CI~~ — GitHub Actions runs pytest (3.13) + frontend lint/build; staging env deploy TBD.
2. Monitoring, rate limits, secret rotation.
3. Load-test search/fitment under concurrency.

### Phase D — Growth features
1. Bulk ops, exports, saved searches.
2. External job ingestion.
3. Accessibility / SEO / mobile polish.

---

## 7. Code quality & security bar (in force)

- Thin routers; logic in `services/`
- Ownership checks return **404** (not 403) for IDOR-sensitive resources
- Uploads: size + MIME + magic bytes (`core/upload_limits.py`)
- Do not skip failing security tests on 500 — fix root cause
- Python tests: **3.13 only** (`apps/api/.venv313`)

Known deferred dependency CVEs: see root README security section (`python-jose` / transitive pins).

---

## 8. How to verify locally

```bash
# API (Python 3.13)
cd apps/api
.\.venv313\Scripts\activate   # Windows
$env:PYTHONPATH="."
python -m pytest tests/security tests/test_schema_validation.py tests/test_fitment_rationale_service.py tests/test_embedding_service.py tests/test_analytics_service.py -v

# Optional Groq smoke
python scripts/groq_audit.py

# Frontend
cd ../..   # repo root
npm run dev
```

API docs: `http://127.0.0.1:8000/docs`
