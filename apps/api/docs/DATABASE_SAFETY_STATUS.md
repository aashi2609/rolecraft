# Database and Migration Safety — Status

**Deploy Python pin:** `3.11.9` (`apps/api/runtime.txt`, `render.yaml`, Cloud Run `app.yaml` → `python311`)  
**Primary Neon endpoint (denylist):** `ep-fragrant-salad-aybt4nuh`  
**Primary alembic:** `c7d8e9f0a1b2` (up to date with repo head)  
**Execution Python:** `3.11.9` (`.venv311`)  

---

## Status Summary

| Part | Description | Status | Notes |
|:---|:---|:---|:---|
| **Part 1** | Safety Net (Guard, Isolation, Backup Policy) | **CLOSED** | Guard rejects primary/missing URLs; backup & restore drill completed by user (Gate 1 passed). |
| **Part 2** | Schema Convergence & Migration | **CLOSED** | `b4c5d6e7f8a9` and `c7d8e9f0a1b2` upgraded cleanly on primary. `alembic current` = `c7d8e9f0a1b2`. |
| **Part 3** | Downgrade Safety & Guardrails | **CLOSED** | Destructive downgrades guarded by `ALLOW_DESTRUCTIVE_DOWNGRADE=1`. |
| **Part 4** | Schema Integrity / GCS Storage Objects | **DEFERRED** | Deferred pending GCP project `ai-crm-501817` billing activation or selection of alternative storage backend. |
| **Part 5** | Migration Tests & CI | **CLOSED** | Pinned Python 3.11.9 in CI and runtime files; test suite isolation validated. |
| **Part 6** | Primary Upgrade & Verification | **CLOSED** | Gate 2 executed with `ALLOW_PRIMARY_MIGRATIONS=1`. Post-upgrade counts matched pre-upgrade counts identically. Smoke test passed. |
| **Part 7** | Test Account Cleanup | **CLOSED** | Gate 3 executed: 273 test accounts deleted via `delete_user_account`. 5 legitimate accounts preserved. Final counts match expected exactly. |

---

## Primary Database Verification Details

### 1. Primary Migration Upgrade (Gate 2)
- Upgraded revisions:
  - `a2b3c4d5e6f7` -> `b4c5d6e7f8a9` (Sync missing enum values for user_role and plan_tier)
  - `b4c5d6e7f8a9` -> `c7d8e9f0a1b2` (Drop legacy message columns thread_id and recipient_id)
- `alembic current` on primary: `['c7d8e9f0a1b2']`
- Pre-upgrade vs Post-upgrade table counts matched identically.

### 2. Smoke Test (Primary API)
- Tested without altering any password hashes:
  - Public job browse (`GET /jobs`): Returned HTTP 200 with 2 jobs.
  - Read thread (`GET /messages/threads/{id}`): Returned HTTP 200 with conversation messages.

### 3. Cleanup of Test Accounts (Gate 3)
- Total users before cleanup: 278
- Keep accounts (5 legitimate accounts preserved):
  - `5f7f4c5d-6fb3-41e1-8b12-5bb7d1670de1` (`kauraashi26@gmail.com`)
  - `b55c77e8-1a01-4f9c-a1ff-4568879121c7` (`sandeepkmallik@gmail.com`)
  - `8ec19047-b287-4f67-ac43-d3bdf4a37069` (`skm7778@gmail.com`)
  - `85e85c0d-06df-4815-b997-241d28bd05bb` (`kauraashi8777@gmail.com`)
  - `86063c04-385b-4632-91b0-143bf11583be` (`admin@acme.com`)
- Deleted accounts: 273 processed via `services.account_deletion_service.delete_user_account` (273 deleted, 0 failed).

### 4. Primary Table Final Counts (Expected vs Actual)

| Table | Expected | Actual | Status |
|:---|:---:|:---:|:---:|
| `users` | 5 | 5 | **MATCH** |
| `candidate_profiles` | 2 | 2 | **MATCH** |
| `companies` | 2 | 2 | **MATCH** |
| `resumes` | 2 | 2 | **MATCH** |
| `job_postings` | 2 | 2 | **MATCH** |
| `subscriptions` | 8 | 8 | **MATCH** |
| `file_records` | 0 | 0 | **MATCH** |
| `applications` | 2 | 2 | **MATCH** |
| `conversations` | 1 | 1 | **MATCH** |
| `messages` | 1 | 1 | **MATCH** |
| `notifications` | 1 | 1 | **MATCH** |
| `hidden_jobs` | 1 | 1 | **MATCH** |

### 5. Local Storage & GCS Status
- Local `uploads` directory check: 0 orphan files left behind.
- Real GCS testing: **DEFERRED** due to GCP project `ai-crm-501817` having billing disabled.
