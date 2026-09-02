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
| Fitment | Mock/heuristic embeddings + **template** rationales (not LLM text yet) |
| Storage | Local `uploads/` or GCS |
| Payments | Mock (Stripe/Razorpay later) |

**Request path:** Browser → `NEXT_PUBLIC_API_URL` → FastAPI `routers/*` → `services/*` → Neon.

**Naming boundary:** API/DB use `snake_case` (`job_role`); frontend uses camelCase (`jobRole`) via mappers in `UserContext` / job pages.

---

## 2. Current completion

| Area | Status | Notes |
|------|--------|--------|
| Backend product APIs | **~95%** | CRUD, search, applications, messages, admin, analytics router |
| Frontend product UI | **~90%** | Full role flows; search/jobs API-backed |
| AI features | **~50%** | Groq live for resume/ATS/parse; fitment still template/heuristic |
| Production readiness | **~40%** | Security fixes + tests in place; staging/CI/monitoring open |

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
- [x] Fitment rationale documented as template-based; company UI shows API `rationale`
- [x] Tests: `tests/security/*`, `tests/test_schema_validation.py` (require `.venv313` / Python 3.13)

### Frontend
- [x] Candidate / company / admin App Router flows
- [x] Company candidate search → `GET /candidates/search` (SEED only as offline fallback)
- [x] Job list/detail mappers include `jobRole` / `jobLevel`
- [x] Plan gating, pricing/checkout (mock pay), settings subscriptions
- [x] Fitment modal: API rationale + “template-based, not AI” note

### Ops / tooling
- [x] Neon + Alembic migrations; `scripts/enable_pgvector.sql`
- [x] `scripts/make_admin.py`, `scripts/groq_audit.py`
- [x] Cloud Run–oriented deploy notes (in root README)

---

## 4. Left to do

### High priority
- [ ] **LLM fitment rationales** — replace template strings; keep UI binding to `rationale`
- [ ] **Real embeddings** — reduce mock/deterministic vectors; refresh on profile change
- [ ] **Staging deploy** — Cloud Run + Vercel (or equivalent) with secrets, CORS locked down
- [ ] **Analytics UI** — wire candidate/company analytics pages fully to `/analytics` (router exists; export/caching polish TBD)
- [ ] Prefer **server-side** filters wherever the API already supports them (reduce remaining client-only filter paths)

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
| `candidates` | `ProfileItemService`, `candidate_search_service` |
| `jobs` | `job_search_service.enrich_job` / `search_jobs`, `fitment_service` |
| `resumes` | `resume_service`, `pdf_service`, Groq via `ai_client` |
| `applications` | Auto-resume via `get_or_generate_resume` |
| `notifications` (+ uploads/subscriptions) | `storage_service`, `subscription_service`, `upload_limits` |
| `admin` | `admin_service` |
| `messages` / `analytics` / `companies` | Domain routers |

---

## 6. Phased roadmap (remaining work only)

### Phase A — AI fitment honesty → quality
1. Keep template rationale until LLM path ships; never invent frontend strings.
2. Add Groq (or equivalent) rationale generation behind a flag; store on `FitmentResult`.
3. Improve embedding pipeline + invalidate on profile/resume change.

### Phase B — Payments & subscriptions
1. Provider SDK + webhooks.
2. Cancel / pause / resume + audit log.
3. Invoices (optional PDF).

### Phase C — Production
1. Staging envs; CI running `pytest` on 3.13 + frontend lint/build.
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
python -m pytest tests/security tests/test_schema_validation.py -v

# Optional Groq smoke
python scripts/groq_audit.py

# Frontend
cd ../..   # repo root
npm run dev
```

API docs: `http://127.0.0.1:8000/docs`
