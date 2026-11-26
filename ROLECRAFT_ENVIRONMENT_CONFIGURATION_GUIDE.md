# ROLECRAFT — Environment Configuration Guide

No real credentials appear in this document or in any committed file.

## Frontend (repo root)

| Variable | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Production: yes** | Browser-side API base (absolute URL). Unset in dev defaults to `http://127.0.0.1:8000`. Production builds **fail** if unset or pointing at localhost (`lib/api.ts`). There is no `/backend` proxy — the frontend is a static export. |
| `NEXT_PUBLIC_WS_URL` | Recommended | WebSocket base (`hooks/useApplicationSocket.ts`). Falls back to `NEXT_PUBLIC_API_URL`. Must be `wss://` in production. |

Files: `.env.local.example` (dev), `.env.production.example` (prod template), `.env.production` (committed, public URLs only).

Production example:

```bash
NEXT_PUBLIC_API_URL=https://api.rolecraft.example.com
NEXT_PUBLIC_WS_URL=wss://api.rolecraft.example.com
```

## Backend (`apps/api`)

Copy `.env.example` → `.env`. Key groups:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db?sslmode=require` — Neon/RDS pooled URL in staging. |
| `JWT_SECRET` | ≥32 chars, random. **Required in production** — app refuses weak/placeholder values. |
| `CORS_ORIGINS` | Comma-separated frontend origins. `*` rejected in production. |
| `ENVIRONMENT` | `development` \| `production`. Production enables all startup guards. |
| `STORAGE_BACKEND` | `local` (dev only — **fatal in production**) \| `gcs`. Future: `s3`. |
| `GCS_BUCKET_NAME` / `GCS_PROJECT_ID` | Required when `STORAGE_BACKEND=gcs`. |
| `PAYMENTS_MODE` | `disabled` (default, 503 on checkout) \| `test` (mock payments via `/payments/mock-complete`) \| `live` (real Razorpay — needs all 3 RAZORPAY_* vars). |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET` | Only for `test`/`live`. Never commit real values. |
| `GROQ_API_KEY` | Resume AI generation. |
| OpenAI embedding key | `text-embedding-3-small`, 1536-dim (Step F). |
| `EMAIL_PROVIDER` | `console` (dev) \| SMTP vars. |
| `FRONTEND_URL` | Used in email links / CORS helpers. |
| `MESSAGING_POLICY` | `applicants_only` etc. |

### Startup validation (production)

`Settings` model validator (`core/config.py`) **refuses to boot** when:
- `JWT_SECRET` missing/weak/<32 chars
- `DATABASE_URL` missing or local placeholder
- `CORS_ORIGINS` missing or contains `*`
- `STORAGE_BACKEND=local` (ephemeral disk — added this branch)

## Payment modes — decision table

| `PAYMENTS_MODE` | Orders endpoint | Completion path | Subscription activation |
|---|---|---|---|
| `disabled` | 503 | n/a | admin grants only |
| `test` | works, `mode:"test"` | `POST /payments/mock-complete` (mock_* payment id) | same `activate_subscription()` as webhook |
| `live` | real Razorpay order | Razorpay Checkout → `/payments/verify` → `/payments/webhook` | webhook only |

## Future AWS mapping (no code changes needed)

| Concern | Mechanism |
|---|---|
| API URL | `NEXT_PUBLIC_API_URL` → ALB/CloudFront API domain; frontend itself on S3+CloudFront |
| Database | `DATABASE_URL` → RDS PostgreSQL 18 + pgvector |
| Storage | `STORAGE_BACKEND` → add `s3` branch in `storage_service.py` (same `object_name` contract) |
| Secrets | AWS Secrets Manager → env vars at deploy time |
| WebSocket | `NEXT_PUBLIC_WS_URL` → `wss://` ALB endpoint; **1 Uvicorn worker** |
