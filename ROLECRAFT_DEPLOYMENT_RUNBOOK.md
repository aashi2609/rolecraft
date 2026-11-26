# ROLECRAFT — Deployment Runbook (Pre-AWS)

## Architecture decision

**Frontend: static export → S3 + CloudFront. Backend: FastAPI (Uvicorn) on EC2/ECS behind ALB.**

`next build` runs with `output: 'export'` and emits a fully static `out/` directory (all routes prerendered, verified: 44 routes, all `○` static, no `ƒ`). There is no Next.js server: no `rewrites()`, no `headers()`, no `/backend` proxy. All browser API calls go cross-origin to `NEXT_PUBLIC_API_URL`.

Dynamic-route strategy: runtime IDs (job/company) are passed as query params on static pages —

| Old (dynamic) route | New (static) route |
|---|---|
| `/jobs/[jobId]` | `/jobs/detail?jobId=<id>` |
| `/companies/[companyId]` | `/companies/profile?companyId=<id>` |
| `/company/jobs/[id]/applications` | `/company/jobs/applications?jobId=<id>` |

`trailingSlash: true` is set, so `out/` contains `path/index.html` files. CloudFront/S3 serve `/path/` natively; requests to `/path` (no slash) need a viewer-request redirect to `/path/` (see below).

## Backend start command (single worker — REQUIRED)

```bash
cd apps/api
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

`--workers 1` is mandatory: the WebSocket connection manager (`core/ws_manager.py`) is **in-memory**. Multiple workers would split connections and break messaging/notifications. Scaling beyond one worker requires a Redis-backed manager (future work).

Health check: `GET /health` (exists in `main.py`).

## Frontend build & deploy (S3 + CloudFront)

```bash
npm ci
NEXT_PUBLIC_API_URL=https://<api-host> \
NEXT_PUBLIC_WS_URL=wss://<api-host> \
npm run build   # → out/
```

Upload `out/` to the S3 bucket and point CloudFront at it (OAC recommended). `API_PROXY_TARGET` is **obsolete** — removed from config; do not set it.

### CloudFront requirements

Full step-by-step (bucket, OAC, function, policy, error pages) lives in [`deploy/README.md`](deploy/README.md) — function source: `deploy/cloudfront-trailing-slash.js`, headers policy template: `deploy/response-headers-policy.json`.

1. **Trailing-slash redirect** — because `trailingSlash: true`, add a viewer-request CloudFront Function (or use the distribution's default behavior) that 301-redirects `/<path>` → `/<path>/` when the URI has no extension and no trailing slash, so `/jobs/detail` reaches `/jobs/detail/index.html`.
2. **Security headers** — the old `next.config.ts` `headers()` no longer applies. Attach a **CloudFront Response Headers Policy** with:

   | Header | Value |
   |---|---|
   | `X-Content-Type-Options` | `nosniff` |
   | `X-Frame-Options` | `DENY` |
   | `Referrer-Policy` | `strict-origin-when-cross-origin` |
   | `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
   | `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-ancestors 'none';` |

   Note: the CSP `connect-src` must also allow the API origin (e.g. `connect-src 'self' https://<api-host> wss://<api-host>`) or browser calls to `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_WS_URL` will be blocked.
3. **Backend `CORS_ORIGINS`** must include the CloudFront domain (e.g. `https://app.example.com`) — all API calls are now cross-origin.
4. **Custom error responses** — map 403/404 to `/404.html` with response code 404 for SPA-ish fallback (optional; all routes are real files).

## Database

1. Provisioned externally (future: RDS PostgreSQL **18** with pgvector — match CI's `pgvector/pgvector:pg18`).
2. `CREATE EXTENSION IF NOT EXISTS vector;`
3. `cd apps/api && alembic upgrade head` — 21 revisions, single head `p8q9r0s1t2u3`.
4. Verify: `alembic heads` (one head), `alembic check` (no model drift).

## Required env vars (see ENVIRONMENT_CONFIGURATION_GUIDE.md)

Backend minimum for staging: `DATABASE_URL`, `JWT_SECRET` (≥32), `CORS_ORIGINS` (must include the CloudFront domain), `ENVIRONMENT=production`, `STORAGE_BACKEND` (gcs or future s3 — **local is fatal in prod**), `PAYMENTS_MODE=disabled|test`, `GROQ_API_KEY`, embedding key.

Frontend minimum: `NEXT_PUBLIC_API_URL` (**required** — production builds fail without a non-localhost value; there is no `/backend` fallback on S3), `NEXT_PUBLIC_WS_URL` for sockets.

## Mock payments in staging/demo

Set `PAYMENTS_MODE=test`. Checkout calls `POST /payments/mock-complete` — completes the subscription with a `mock_` payment id through the same activation path as real webhooks. No real money moves. Flip to `live` + Razorpay secrets when credentials arrive — zero code changes.

## Pre-deploy checklist

- [ ] `ENVIRONMENT=production` boot test passes (all startup guards green)
- [ ] `alembic upgrade head` clean on a **disposable** DB first
- [ ] `PAYMENTS_MODE` deliberately chosen (`test` for demo, `disabled` for no-checkout)
- [ ] `STORAGE_BACKEND` ≠ local in production
- [ ] Uvicorn `--workers 1`
- [ ] `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_WS_URL` point at the real API host (build fails on localhost or when unset)
- [ ] CloudFront response-headers policy carries the security headers + CSP above
- [ ] Backend `CORS_ORIGINS` includes the CloudFront domain
- [ ] CloudFront trailing-slash redirect configured (`trailingSlash: true`)
- [ ] TLS on CloudFront; `wss://` for sockets
- [ ] Secrets injected via Secrets Manager/env — nothing in the repo

## Rollback

- Code: redeploy previous image/commit (frontend: redeploy previous `out/` build to S3).
- DB: Alembic downgrade is supported but destructive steps require `ALLOW_DESTRUCTIVE_MIGRATION=1` (see migration e6c7d8e9f0a1). Prefer forward-fix migrations.
- Payments: `PAYMENTS_MODE=disabled` instantly stops checkout without redeploy.
