# ROLECRAFT — Deployment Blocker Fix Report

Date: 2026-11-24 · Branch: `chore/pre-aws-readiness`

Every blocker below was verified against the current code before fixing.

## A. Payment — mock mode (FIXED)

### Verified problems found

| # | Problem | Evidence |
|---|---------|----------|
| 1 | Frontend called `POST /api/payments/create-order` — **route does not exist** (no `app/api/` dir) → every checkout 404'd | `lib/payment.ts` (old), `find app -path "*api*"` → empty |
| 2 | Wrong contract even if route existed: sent `{planId, billingPeriod}`, expected `razorpay_order_id`/`razorpay_key_id`; backend expects `{plan_tier, billing_period}` → `{order_id, key, amount, email, currency}` | `apps/api/routers/payments.py` `OrderCreateRequest/Response` |
| 3 | Auth token read from `authToken`/`sessionStorage` — real key is `rolecraft_token` in localStorage (`lib/api.ts`) | old `getAuthToken()` |
| 4 | `UserContext.setPlan()` updated local plan state **even when the API call failed** — paid plan shown without server grant | `context/UserContext.tsx` catch-fallback |
| 5 | Checkout called `setPlan()` after payment → `POST /subscriptions` **cancels live subs and creates pending** — would have revoked the just-activated paid subscription | `services/subscription_service.py::upsert_subscription` |
| 6 | Checkout collected raw card number / expiry / CVV / UPI / bank / wallet — **never transmitted anywhere** | `app/(public)/checkout/page.tsx`, `lib/payment.ts` validators |
| 7 | `PAYMENTS_MODE=disabled` was not enforced — `/payments/orders` and `/payments/verify` still ran (the covering test was an empty stub) | `routers/payments.py` (no check), `tests/test_payment_verification.py:648` |
| 8 | No way to complete a mock payment end-to-end: activation requires a Razorpay webhook that never arrives in test mode | `payment_service.process_webhook` → `activate_subscription` |

### Fixes applied

**Backend — `apps/api/routers/payments.py`**
- `POST /payments/orders` and `POST /payments/verify` → **503** when `PAYMENTS_MODE=disabled`.
- New `POST /payments/mock-complete` (`{order_id}`): hard-gated on `PAYMENTS_MODE=test` (403 otherwise). Finds the caller's transaction, marks it `completed` with a clearly-marked `mock_<hex>` payment id, then calls the **same** `activate_subscription()` used by the verified webhook — no shortcut, full audit log. Response includes `mock: true`.
- `OrderCreateResponse` gains `mode` field so the client knows which path to take.

**Frontend — `lib/payment.ts`**
- `processPayment()` rewritten to the real contract: `POST {API_URL}/payments/orders` with `{plan_tier, billing_period}` (`lifetime` for `corporate_lifetime`, else `annual`/`monthly` from `isAnnual`).
- `mode === 'test'` → calls `/payments/mock-complete`, returns `{success, mock: true}` — no Razorpay modal, no fake checkout.
- `mode === 'live'` → opens real Razorpay Checkout, then `POST /payments/verify` with `order_id`/`payment_id`/`signature` before reporting success.
- Auth now uses `getToken()` from `lib/api.ts` (correct `rolecraft_token` key).
- `API_URL` exported from `lib/api.ts` (same `/backend` proxy / `NEXT_PUBLIC_API_URL` resolution as every other call).

**Frontend — `context/UserContext.tsx`**
- `setPlan()` no longer swallows API errors and still sets the plan locally — it now throws on failure so callers can't claim an ungranted plan.

**Frontend — `app/(public)/checkout/page.tsx`**
- Removed all payment-method tabs and every card/CVV/UPY/bank/wallet input — none of it was ever sent. Replaced with a "Payment" info card.
- After successful payment calls `refreshSession()` (re-reads `/subscriptions/me`) instead of `setPlan()` — the server is the only authority on the activated plan.

**Tests — `apps/api/tests/test_payment_verification.py`**
- Implemented the previously-empty `test_payments_mode_disabled_blocks_orders` (asserts 503 on orders + verify).
- Added `test_mock_complete_rejected_when_payments_disabled` (403).
- Added `test_mock_complete_activates_subscription_in_test_mode` — full path: order → mock-complete → subscription `active`, `mock_` payment id asserted.

### How mock payment works now

```
PAYMENTS_MODE=test:
  POST /payments/orders        → {order_id, key, amount, mode:"test"}
  POST /payments/mock-complete → marks txn completed (mock_* id), activates sub
  GET  /subscriptions/me       → plan active

PAYMENTS_MODE=live (future):
  POST /payments/orders        → real Razorpay order
  Razorpay Checkout modal      → user pays
  POST /payments/verify        → signature check
  POST /payments/webhook       → server-to-server activation

PAYMENTS_MODE=disabled (default):
  POST /payments/orders|verify → 503; admin grants only
```

### Path to real Razorpay later

Set `PAYMENTS_MODE=live` + `RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET`. No code changes needed — the live branch in `processPayment()` and the webhook path already exist. The mock endpoint stays harmless (403 in live mode).

## B. Next.js hosting — DECISION: SSR (Option 2)

`next.config.ts` uses server `rewrites()` + `headers()`; dynamic routes exist; `lib/api.ts` defaults browser calls to same-origin `/backend` proxy. **Static export is not viable** without rewriting routing/API architecture. Frontend + FastAPI run as two processes on one EC2 (or separate services). S3+CloudFront static hosting is NOT supported by the current architecture — documented in the runbook.

## C. File storage (FIXED)

- Verified: all uploads go through `services/storage_service.py::upload_file()` behind `storage_backend = local | gcs`; downloads via authenticated `/files/` routes; path-traversal guard `_assert_safe_object_path`.
- **Fix:** `core/config.py` now **refuses to start in production with `STORAGE_BACKEND=local`** (ephemeral-disk data loss). Added regression test `test_production_fails_with_local_storage_backend`.
- Future S3: add `elif settings.storage_backend == "s3"` branch using boto3 against the same `object_name`/`storage_path` contract — no business-logic changes. Documented in env guide.

## D. Subscription ORM (FIXED)

- `User.subscription` was `uselist=False` over **all** subscription rows — users accumulate cancelled rows → `MultipleRowsFound` on any eager load/refresh.
- **Fix:** `primaryjoin` scoped to `status IN ('pending','active')` (`models/__init__.py`). History preserved; `get_current_subscription()` unchanged; `lazy="raise"` already prevented implicit loads. Verified no code eager-loads `User.subscription` except `db.refresh` in `user_service.py`.

## E. WebSocket (DOCUMENTED, no code change needed)

In-memory `ws_manager` → **exactly 1 Uvicorn worker**. `render.yaml` already runs without `--workers` (default 1). Runbook documents the constraint; multi-worker requires Redis-backed manager (future work, not a blocker for single-instance staging).

## F. Environment/config (FIXED)

- Backend `.env.example` already complete; clarified `PAYMENTS_MODE=test` mock semantics.
- Frontend `.env.local.example` / `.env.production.example` already document `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`, `API_PROXY_TARGET`; `lib/api.ts` **fails production builds** if API URL is unset/localhost.
- `.env.production` committed contains only public URLs — no secrets. `.env*` gitignored otherwise.
