# ROLECRAFT — Final Pre-AWS Infrastructure Deployment Readiness Audit

**Audit date:** 2026-11-26 (revised — S3 static-frontend requirement)
**Auditor role:** Independent DevOps/deployment-readiness audit (read-only)
**Mode:** READ-ONLY — no code modified, no commits, no AWS resources touched.
**Requirement delta:** Frontend MUST be deployable as static files to **S3 + CloudFront** (not SSR/EC2).

---

## 1. Repository & Branch Verification

| Item | Value |
|---|---|
| Repository | `https://github.com/aashi2609/rolecraft` |
| Branch | `chore/pre-aws-readiness` |
| HEAD commit | `5f84bd9` — `ci: make mypy blocking` |
| Commits ahead of `origin/main` | 3 (`cf0d26f`, `29fcbd1`, `5f84bd9`) |
| Uncommitted changes | None — tree clean |
| Unrelated modifications | None — all 19 files in payment/subscription/storage/env/report scope |

## 2. Frontend Local Readiness — S3 STATIC EXPORT ASSESSMENT

| Check | Result |
|---|---|
| TypeScript `npx tsc --noEmit` | PASS — 0 errors |
| ESLint | PASS — 0 errors |
| Production build `npm run build` | PASS — Next.js 16.4.6, 41 routes |
| Dynamic routes in build | `/jobs/[jobId]`, `/companies/[companyId]`, `/company/jobs/[id]/applications` → `ƒ` **server-rendered on demand** |
| `generateStaticParams` | **Absent everywhere** — no dynamic route can pre-render at build time |
| `next.config.ts` server features | `rewrites()` (`/backend/*` proxy) + `headers()` (security headers + CSP) — **both unsupported under `output: 'export'`** |
| Same-origin `/backend` proxy | `lib/api.ts` defaults browser calls to `/backend` — requires the Next.js server; static hosting has no server to rewrite |
| Absolute API URL support | ✅ `NEXT_PUBLIC_API_URL` supported and enforced non-localhost in prod builds |
| WebSocket URL | ✅ `NEXT_PUBLIC_WS_URL` configurable |
| Auth | ✅ client-side `localStorage` JWT — static-compatible |

### Static-export blocker analysis (Category A — developer action required)

| # | File | Blocker | Why it blocks S3 export |
|---|---|---|---|
| F1 | `next.config.ts` | `async rewrites()` + `async headers()` | `output: 'export'` cannot use server rewrites/headers — build fails or silently drops them. Security headers + CSP must move to **CloudFront response-headers policy**; `/backend` proxy must be replaced by absolute `NEXT_PUBLIC_API_URL` calls. |
| F2 | `app/jobs/[jobId]/`, `app/(public)/companies/[companyId]/` (and any `[id]` route) | Dynamic segments with runtime IDs, no `generateStaticParams` | Static export requires every path known at build time. Job/company IDs are runtime DB data — cannot enumerate. Requires refactor: query-param routing, catch-all client rendering, or ISR-style rewrite — **architectural change, not config**. |
| F3 | `lib/api.ts` default `/backend` | Same-origin proxy assumption | Works only if `NEXT_PUBLIC_API_URL` is set — code supports it, but every call path must be verified to use the absolute URL (CORS then applies — backend `CORS_ORIGINS` must include the CloudFront domain). |
| F4 | Server components / server actions | Not fully audited page-by-page | Any `'use server'` actions or server-side data fetching break static export. Spot evidence: pages are client-heavy (`"use client"` widespread) but a complete audit is required. |

**Static export is NOT currently possible.** The app was built as SSR. Making it S3-static-compatible is a real refactor (dynamic routing strategy + config migration + full client-render audit).

## 3. Backend Local Readiness — ✅ READY

| Check | Result |
|---|---|
| Deps | `requirements.txt` + venv `.venv311` (Python 3.11.9) — all imports resolve |
| Startup guards | `core/config.py` refuses prod boot without strong `JWT_SECRET`, real `DATABASE_URL`, non-wildcard `CORS_ORIGINS`, non-local `STORAGE_BACKEND` |
| Health | `GET /health` (`main.py:305`) |
| AuthN/Z, file auth, error safety | Security suite PASS (local + CI) |
| Linux service | `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1` — Linux boot itself NOT VERIFIED locally |

## 4. Database Readiness — ✅ READY

- 21 migrations, single head `p8q9r0s1t2u3`, full chain executed on disposable Neon DB + CI pg18; `alembic check` clean.
- pgvector required (`CREATE EXTENSION vector`, 1536-dim embeddings).
- `User.subscription` ORM safe (live-scoped `primaryjoin`, history preserved).
- **AWS note:** provision **RDS PostgreSQL 18** (match CI/Neon); pgvector must be installed/available.

## 5. Mock Payment — ✅ READY

`PAYMENTS_MODE=test` + `POST /payments/mock-complete` (`mock_*` IDs, same activation path as webhook); disabled → 503; FE/BE contract aligned; no paid grant on failure. Tests PASS.

## 6. File Storage — ✅ READY (S3 = small code task)

`storage_service.py` abstraction (`local`/`gcs`); prod refuses `local`. **For S3 uploads bucket:** add `elif storage_backend == "s3"` boto3 branch (~30 lines) + `S3_BUCKET`/`AWS_REGION` env — Category A-lite, schedule with developer. Separate from the frontend-static issue.

## 7. WebSocket — ✅ READY (single worker)

JWT ticket auth, in-memory manager → **exactly 1 Uvicorn worker**; `NEXT_PUBLIC_WS_URL` → `wss://` ALB/CloudFront domain.

## 8. Docker & CI/CD

- **No Dockerfiles** — none present. If frontend goes static→S3 and backend→EC2/ECS, backend image still needed for ECS; EC2+systemd needs none.
- CI: `ci.yml` hardened — ruff, **mypy blocking (0 errors)**, pip-audit, pg18, alembic, pytest **329 passed / 0 skipped** (run `45470286700`), failure propagation proven.

## 9. Environment Variables

Frontend: `NEXT_PUBLIC_API_URL` (required for static — no `/backend` proxy exists), `NEXT_PUBLIC_WS_URL`, ~~`API_PROXY_TARGET`~~ (obsolete under static export).
Backend: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS` (must include CloudFront domain), `ENVIRONMENT=production`, `STORAGE_BACKEND`, `GCS_*`/`S3_*`, `PAYMENTS_MODE`, `GROQ_API_KEY`, embedding key, `EMAIL_PROVIDER`, `FRONTEND_URL`, `MESSAGING_POLICY`.
No committed secrets; gitleaks in CI.

## 10. Category Separation

### Category A — Developer-side blockers (frontend static export)

| ID | File | Issue | Required fix |
|---|---|---|---|
| F1 | `next.config.ts` | `rewrites()`/`headers()` incompatible with `output:'export'` | Remove server functions; move headers/CSP to CloudFront policy; drop `API_PROXY_TARGET` requirement |
| F2 | `app/**/[param]` routes | Dynamic segments can't enumerate at build | Choose strategy: client-side catch-all, query-param routes, or hybrid SSR for those pages only |
| F3 | `lib/api.ts` + all callers | `/backend` proxy default | Set `NEXT_PUBLIC_API_URL` everywhere; audit every fetch uses it; add CloudFront domain to backend `CORS_ORIGINS` |
| F4 | app-wide | Unverified server components/actions | Audit for `'use server'`/server data fetching; convert or exclude |

### Category B — AWS infrastructure tasks

S3 bucket (static site) + CloudFront distribution + OAC + response-headers policy + Route53/domain + ACM cert; ALB → EC2/ECS backend; RDS PostgreSQL 18 + pgvector; IAM roles; Secrets Manager; security groups; `wss://` endpoint; `alembic upgrade head` on RDS.

## 11. Final Verification — Commands & Results

| Check | Result |
|---|---|
| `npx tsc --noEmit` / `eslint` / `npm run build` | PASS |
| `output:'export'` build attempt | **NOT RUN — known-incompatible config present (F1/F2); would fail or produce broken dynamic routes** |
| Backend pytest subsets (local Neon) | PASS — 69 tests |
| Subscription suite | PASS — 48 tests |
| `alembic upgrade head` fresh DB | PASS — 21 revisions |
| CI run `45470286700` | PASS — 329 tests, 0 skipped |
| Linux `uvicorn`/`npm start` boot | NOT VERIFIED (no Linux env) |
| Docker build | NOT VERIFIED (no Dockerfiles) |

## 12. Final Verdict

# ⛔ NOT READY — DEVELOPER ACTION REQUIRED (frontend static export)

**For the S3+CloudFront frontend requirement specifically:** the application **cannot** be statically exported today. Four Category-A blockers (F1–F4 above) must be fixed by the developer first — primarily `next.config.ts` server features and dynamic-route strategy.

**Everything else IS ready:** backend, database, payments, storage abstraction, websockets, CI, secrets — all verified.

**Practical path forward:**
1. Developer resolves F1–F4 (est. refactor: config + dynamic routing + client-render audit).
2. Re-run `output:'export'` build verification.
3. Then AWS infra can proceed: S3+CloudFront (frontend), EC2/ECS+ALB (API), RDS PG18+pgvector, S3 uploads bucket (+ `s3` storage branch).

**Alternative if timeline matters:** deploy frontend as SSR on EC2 now (zero code changes, audit previously verified READY), and schedule the static-export refactor separately. S3 is then only needed for user uploads.

---
*This audit is evidence-based; every PASS cites an executed command. Items marked NOT VERIFIED require the stated environment.*
