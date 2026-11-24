# ROLECRAFT — Pre-AWS Deployment Baseline

Date: 2026-11-24
Branch: `chore/pre-aws-readiness` (created from `fix/mypy-cleanup` @ `77d9c32`). Working tree at baseline: clean.

## Repository

- Repo: `https://github.com/aashi2609/rolecraft`
- Layout: Next.js frontend at repo root (`app/`, `components/`, `lib/`, `context/`, `hooks/`); FastAPI backend at `apps/api/`
- Package manager: npm (`package-lock.json`), Node pinned via `.nvmrc` = `20.19.0`
- Python pinned via `.python-version` = `3.11.9`; backend deps in `apps/api/requirements.txt`

## Frontend architecture

- Next.js App Router, TypeScript, client-heavy SPA-style UI.
- `next.config.ts` uses **server-side `rewrites()`** (`/backend/:path*` → `API_PROXY_TARGET`) and **`headers()`** (security headers + CSP). These are server features → **SSR/Node hosting is required**; `output: 'export'` is NOT compatible.
- Dynamic routes exist (`app/(company)/company/messages`, job detail routes) — static export would break them.
- API base URL: `lib/api.ts` reads `NEXT_PUBLIC_API_URL`, **throws at build time in production if unset or localhost** — already deployment-safe.
- WebSocket URL: `hooks/useApplicationSocket.ts` reads `NEXT_PUBLIC_WS_URL` (falls back to `NEXT_PUBLIC_API_URL`), throws if unconfigured.
- `.env.production` is committed but contains **only public URLs** (Render domain) — no secrets. `.env*` is gitignored except `.env.production` + `.env.production.example`.
- Env examples present: `.env.local.example`, `.env.production.example` (documents `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`, `API_PROXY_TARGET`).

## Backend architecture

- FastAPI + async SQLAlchemy + asyncpg + Alembic + pgvector; Pydantic schemas.
- Entry: `apps/api/main.py` (`uvicorn main:app`). `render.yaml` exists (Render deploy config, Python runtime, `pip install -r requirements.txt`, `uvicorn main:app --host 0.0.0.0 --port $PORT`).
- Startup validation: `core/config.py` fails in production when `JWT_SECRET`, `DATABASE_URL`, `CORS_ORIGINS` are missing/weak/placeholder; dev mode generates random JWT secret.
- Rate limiting, query profiler, timeout middleware, upload limits, db_guard (primary-DB protection) all present in `core/`.
- WebSocket: in-memory `core/ws_manager.py` + ticket auth (`core/websocket_ticket.py`, `core/websocket_auth.py`) → **single Uvicorn worker only**.

## Database & migrations

- PostgreSQL + pgvector. 21 Alembic revisions, single head `p8q9r0s1t2u3` (verified in CI: `alembic heads`, upgrade on fresh pg18, `alembic check` → no drift).
- CI uses `pgvector/pgvector:pg18`; migrations use standard DDL (no `CREATE INDEX CONCURRENTLY` outside transaction concerns observed).
- Enums synced via dedicated migration `b4c5d6e7f8a9`.

## Payment implementation (current)

- `core/payment_config.py`: `PAYMENTS_MODE` = `disabled | test | live`.
  - `disabled`: payment endpoints blocked.
  - `test`: **mocked provider calls** — Razorpay SDK calls are stubbed; key-id/secret/webhook-secret optional with warnings. This IS the mock/demo mode required by the task.
  - `live`: requires real Razorpay credentials (not configured, not to be added now).
- `services/payment_service.py`: order creation, webhook signature verification (raw-body HMAC), idempotent webhook events (`uq_webhook_event_provider_event_id`), amount verification, unique partial index `idx_user_live_subscription` prevents duplicate live subscriptions, subscription activation only after verified payment.
- Admin cannot manually activate subscriptions (PATCH rejects `status=active`); activation only via verified payment path or admin grant endpoint with audit log.
- Frontend: `lib/payment.ts` + checkout UI exist; need final contract verification (see blocker report).

## File storage

- `services/storage_service.py`: abstraction with `storage_backend = local | gcs` (`core/config.py`).
  - `local`: writes under configured upload dir; `get_local_file_path` path-traversal-safe.
  - `gcs`: `google-cloud-storage` client, signed URLs.
- All uploads flow through `upload_file()`; downloads via `routers/files.py` with per-resource authorization (owner / applying company / admin) — verified by `tests/security/test_file_serving.py` + `test_step_c_resume_access.py`.
- **Gap:** no `s3` backend and no warning when `ENVIRONMENT=production` + `STORAGE_BACKEND=local` (ephemeral-disk risk). Fix: add config validation warning/fail + document S3 path.

## Subscription ORM

- `User.subscription`: `uselist=False, lazy="raise"` — **was unsafe**: users accumulate cancelled rows; any eager load/refresh spanning >1 row → `MultipleRowsFound`.
- **Fixed in this branch:** `primaryjoin` scoped to `status IN ('pending','active')`; history preserved in table; `get_current_subscription()` remains the canonical reader. `lazy="raise"` means no production code path eager-loads it implicitly; only `db.refresh` in `user_service.py`.

## Environment variables (backend, from `.env.example`)

`DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `GCS_BUCKET_NAME`, `GCS_PROJECT_ID`, `GROQ_API_KEY`, `CORS_ORIGINS`, `ENVIRONMENT`, `STORAGE_BACKEND`, `EMAIL_PROVIDER`, `FRONTEND_URL`, `MESSAGING_POLICY`, `PAYMENTS_MODE`, `RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET`. OPENAI key for embeddings (Step F). All secrets blank in example — good.

## Deployment blockers identified

1. **Subscription ORM `uselist=False`** — FIXED (primaryjoin scoping).
2. **No prod guard for local storage backend** — add startup warning/error when `ENVIRONMENT=production` and `STORAGE_BACKEND=local`.
3. **Single-worker WebSocket constraint undocumented in run config** — document + provide start command with `--workers 1`.
4. **`.env.production` is Render-specific** — acceptable for now; AWS phase will supply real values. Documented, not a code blocker.
5. Frontend/backend payment contract + token-key + raw-card fields — verify against `lib/payment.ts` and checkout components (see fix report).

## CI/CD

- `.github/workflows/ci.yml` — single workflow; ruff, mypy (0 errors), pip-audit (57 documented ignores), pg18 service, alembic heads/upgrade/check, pytest 326 tests + junit skip-gate, artifacts `if: always()`. Last full run GREEN.
- `api-ci.yml` duplicate was deleted previously.
