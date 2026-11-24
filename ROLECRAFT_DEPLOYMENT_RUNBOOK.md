# ROLECRAFT — Deployment Runbook (Pre-AWS)

## Architecture decision

**Next.js SSR (Node) + FastAPI (Uvicorn), two processes — initially co-located on one EC2.**

Static export (`output: 'export'`) is **NOT supported**: the app uses server `rewrites()`/`headers()` in `next.config.ts`, dynamic App Router routes, and a same-origin `/backend` proxy. S3+CloudFront static hosting would require a routing rewrite — out of scope.

## Backend start command (single worker — REQUIRED)

```bash
cd apps/api
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

`--workers 1` is mandatory: the WebSocket connection manager (`core/ws_manager.py`) is **in-memory**. Multiple workers would split connections and break messaging/notifications. Scaling beyond one worker requires a Redis-backed manager (future work).

Health check: `GET /health` (exists in `main.py`).

## Frontend start command

```bash
npm ci
NEXT_PUBLIC_API_URL=https://<api-host> \
NEXT_PUBLIC_WS_URL=wss://<api-host> \
API_PROXY_TARGET=https://<api-host> \
npm run build && npm start
```

`next start` serves SSR on port 3000. Put nginx/ALB in front for TLS termination.

## Database

1. Provisioned externally (future: RDS PostgreSQL **18** with pgvector — match CI's `pgvector/pgvector:pg18`).
2. `CREATE EXTENSION IF NOT EXISTS vector;`
3. `cd apps/api && alembic upgrade head` — 21 revisions, single head `p8q9r0s1t2u3`.
4. Verify: `alembic heads` (one head), `alembic check` (no model drift).

## Required env vars (see ENVIRONMENT_CONFIGURATION_GUIDE.md)

Backend minimum for staging: `DATABASE_URL`, `JWT_SECRET` (≥32), `CORS_ORIGINS`, `ENVIRONMENT=production`, `STORAGE_BACKEND` (gcs or future s3 — **local is fatal in prod**), `PAYMENTS_MODE=disabled|test`, `GROQ_API_KEY`, embedding key.

Frontend minimum: `NEXT_PUBLIC_API_URL`, `API_PROXY_TARGET` (+ `NEXT_PUBLIC_WS_URL` for sockets).

## Mock payments in staging/demo

Set `PAYMENTS_MODE=test`. Checkout calls `POST /payments/mock-complete` — completes the subscription with a `mock_` payment id through the same activation path as real webhooks. No real money moves. Flip to `live` + Razorpay secrets when credentials arrive — zero code changes.

## Pre-deploy checklist

- [ ] `ENVIRONMENT=production` boot test passes (all startup guards green)
- [ ] `alembic upgrade head` clean on a **disposable** DB first
- [ ] `PAYMENTS_MODE` deliberately chosen (`test` for demo, `disabled` for no-checkout)
- [ ] `STORAGE_BACKEND` ≠ local in production
- [ ] Uvicorn `--workers 1`
- [ ] `NEXT_PUBLIC_API_URL`/`API_PROXY_TARGET` point at the real API host (build fails on localhost)
- [ ] TLS terminated at ALB/nginx; `wss://` for sockets
- [ ] Secrets injected via Secrets Manager/env — nothing in the repo

## Rollback

- Code: redeploy previous image/commit.
- DB: Alembic downgrade is supported but destructive steps require `ALLOW_DESTRUCTIVE_MIGRATION=1` (see migration e6c7d8e9f0a1). Prefer forward-fix migrations.
- Payments: `PAYMENTS_MODE=disabled` instantly stops checkout without redeploy.
