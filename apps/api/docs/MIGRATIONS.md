# Database Migration Policy

## Overview

This document defines the migration policy for the RoleCraft PostgreSQL database, including safety guards, downgrade procedures, and production deployment guidelines.

## Core Principles

1. **Never run migrations automatically on app startup in production**
2. **All production migrations require explicit approval**
3. **Destructive changes must use expand-then-contract pattern**
4. **Always test migrations on a Neon branch before production**
5. **Rollback means restore, not downgrade**

## Production Rollback Policy

**CRITICAL**: Production rollback does NOT mean `alembic downgrade`. Downgrade migrations are intentionally blocked for destructive changes.

### Approved Rollback Methods

1. **Restore from backup**: Use the latest GCS backup (see `docs/BACKUP_AND_RECOVERY.md`)
2. **Neon PITR branch**: Create a branch from a timestamp before the failed migration
3. **Corrective forward migration**: Write a new migration to fix the issue

### Why Not Downgrade?

- Downgrade migrations for destructive changes are guarded by `ALLOW_DESTRUCTIVE_DOWNGRADE=1`
- Data loss is irreversible in many downgrades (dropped columns/tables)
- Enum value additions cannot be reverted in PostgreSQL
- The expand-then-contract pattern makes downgrades complex and error-prone

## Migration Deployment Procedure

### Pre-Deployment Checklist

1. **Create a Neon branch from primary**
   ```bash
   neonctl branches create --parent-id <primary-endpoint>
   ```

2. **Set environment for branch testing**
   ```bash
   export DATABASE_URL=<branch-connection-string>
   export TEST_DATABASE_URL=<branch-connection-string>
   ```

3. **Run migration on branch**
   ```bash
   alembic upgrade head
   ```

4. **Verify migration**
   - Check row counts before/after
   - Run smoke tests
   - Verify application functionality

5. **Take a fresh backup of primary**
   ```bash
   python scripts/backup_db.py
   ```

### Production Deployment

1. **Set approval flag for single command only**
   ```bash
   ALLOW_PRIMARY_MIGRATIONS=1 alembic upgrade head
   ```

   **IMPORTANT**: Never set `ALLOW_PRIMARY_MIGRATIONS=1` in `.env` or environment files. Set it only for the specific migration command.

2. **Verify migration**
   - Compare row counts with branch results
   - Run smoke tests (sign in, list jobs, send message)

3. **If anything differs from branch result, STOP and report**

## Expand-Then-Contract Pattern

For destructive schema changes (dropping columns/tables), use two separate migrations across two releases:

### Phase 1: Expand (Release N)

- Add new columns/tables alongside old ones
- Backfill data
- Keep old columns/tables
- Deploy application code to use both old and new paths

### Phase 2: Contract (Release N+1)

- Drop old columns/tables
- Remove backward compatibility code
- Deploy application code that only uses new paths

**Example**: The conversation model migration
- `e6c7d8e9f0a1`: Add conversations table, keep thread_id/recipient_id
- `c7d8e9f0a1b2`: Drop thread_id/recipient_id (after verification)

## Safety Guards

### Database Isolation Guard

Located in `core/db_guard.py`:

- Prevents tests from running against production database
- Uses endpoint ID denylist for known production endpoints
- Normalizes Neon pooled vs direct URLs
- Fails loudly if `TEST_DATABASE_URL` is not set

### Test Configuration

Located in `tests/conftest.py`:

- Sets `DATABASE_URL = TEST_DATABASE_URL` BEFORE any imports
- Ensures tests never load production database URL
- Validates Python version (>= 3.10)

### Migration Guard

Located in `alembic/env.py`:

- Requires either `TEST_DATABASE_URL` or `ALLOW_PRIMARY_MIGRATIONS=1`
- Refuses to run migrations against primary without explicit opt-in
- Checks endpoint ID against denylist

### Downgrade Guards

Destructive downgrades are guarded by `ALLOW_DESTRUCTIVE_DOWNGRADE=1`:

- `0001_initial`: Drops all tables (catastrophic)
- `0002_resume_ai`: Drops resume AI columns
- `9d87f0721ccf`: Drops hidden_jobs table and job location columns
- `f7a8b9c0d1e2`: Drops file_records table (access control for uploads)
- `a1b2c3d4e5f6`: Drops message recipient_id
- `b3c4d5e6f7a8`: Drops stale resume tracking columns
- `a2b3c4d5e6f7`: Drops token_version (breaks session invalidation)
- `e6c7d8e9f0a1`: Drops conversations table (major schema change)
- `c7d8e9f0a1b2`: Re-adds legacy message columns (contract migration)

## Migration Testing

### Local Testing

```bash
# Set up local test database
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/rolecraft_test"

# Run full test suite
pytest

# Run migration tests (when implemented)
pytest tests/test_migrations.py
```

### CI/CD Testing

GitHub Actions should:

1. Start Postgres service with pgvector enabled
2. Set `TEST_DATABASE_URL`
3. Run `alembic heads` (must return exactly one head)
4. Run `alembic upgrade head` on empty database
5. Run `alembic check` (must report no drift)
6. Run migration tests
7. Run full test suite

## Enum Value Management

PostgreSQL does not support `ALTER TYPE ... DROP VALUE`. This means:

- Adding enum values is safe (idempotent with `IF NOT EXISTS`)
- Removing enum values requires recreating the type and all referencing tables
- **Never remove enum values in production**

When adding enum values in migrations:

```python
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'new_value';")
```

The `autocommit_block()` is required because `ALTER TYPE` cannot run inside a transaction.

## Plan-Tier Migration

### Legacy Values

- `free`, `basic`, `premium`, `elite`, `starter`, `growth`, `scale`

### New Values

- `resume_builder`, `job_search`, `complete`, `corporate_annual`, `corporate_lifetime`

### Migration Strategy

**TO BE DETERMINED**: Product decision required for mapping legacy values to new values.

Current entitlement code behavior with legacy values needs analysis before proposing a mapping.

## Messages Quarantine Table

The `messages_quarantine` table is created during the conversation model migration (`e6c7d8e9f0a1`) to preserve messages that could not be mapped to valid conversations.

**Policy**:
- Keep this table on production (it may contain real data needing human review)
- Never auto-drop it
- Review quarantined messages periodically
- Create a documented process for reviewing and resolving quarantined messages

## Troubleshooting

### Migration Fails on Production

1. Stop immediately
2. Check the error message
3. If data corruption: restore from backup
4. If schema issue: create corrective forward migration
5. Never attempt to downgrade without explicit approval

### Tests Fail After Migration

1. Check if test database schema is up to date
2. Run `alembic upgrade head` on test database
3. Verify migration didn't break test fixtures
4. Update test fixtures if needed

### `alembic check` Reports Drift

1. Identify what changed outside Alembic
2. Create a migration to bring Alembic in sync
3. Or document why the drift is intentional (rare)

## Contact

For migration-related questions or issues:
- Database Administrator: [TO BE FILLED]
- Engineering Lead: [TO BE FILLED]
