# Backup and Recovery Guide

## Overview

This document describes the backup and recovery procedures for the RoleCraft PostgreSQL database.

## What is Backed Up

- **Full database dumps**: Complete PostgreSQL database including all tables, indexes, constraints, and data
- **Frequency**: Daily backups (can be scheduled via cron or CI/CD)
- **Format**: Custom PostgreSQL format (compressed, allows selective restores)
- **Location**: Private Google Cloud Storage bucket (outside Neon infrastructure)

## Backup Location

- **GCS Bucket**: `rolecraft-backups` (configured via `GCS_BACKUP_BUCKET` environment variable)
- **Naming Convention**: `rolecraft_backup_YYYYMMDD_HHMMSS.sql.gz`
- **Retention**: Versioning enabled on bucket (retention policy TBD)

## Who Can Restore

- Database administrators with GCS bucket access
- DevOps engineers with appropriate IAM permissions
- No credentials are stored in the repository

## Backup Procedure

### Automated Daily Backup

The backup script can be scheduled via cron:

```bash
# Run daily at 2 AM UTC
0 2 * * * cd /path/to/rolecraft/apps/api && python scripts/backup_db.py
```

### Manual Backup

```bash
cd /path/to/rolecraft/apps/api
export DATABASE_URL="postgresql+asyncpg://user:pass@host/db"
export GCS_BACKUP_BUCKET="rolecraft-backups"
python scripts/backup_db.py
```

## Restore Procedure

### Prerequisites

1. PostgreSQL client tools installed (`pg_dump`, `pg_restore`)
2. Google Cloud SDK installed (`gsutil`)
3. GCS bucket access configured (`gsutil config` or service account key)

### Emergency Restore

```bash
cd /path/to/rolecraft/apps/api
export DATABASE_URL="postgresql+asyncpg://user:pass@host/db"
export GCS_BACKUP_BUCKET="rolecraft-backups"
export BACKUP_FILENAME="rolecraft_backup_20261026_020000.sql.gz"  # optional
python scripts/restore_db.py
```

If `BACKUP_FILENAME` is not specified, the script will use the latest backup.

### Point-in-Time Recovery (Neon)

Neron provides point-in-time recovery via branching:

```bash
# Create a branch from a specific timestamp
neonctl branches create --parent-id <primary-endpoint> --timestamp "2026-10-25 23:00:00"

# Or via Neon Console
# Console → Branches → Create Branch → Select timestamp
```

**PITR Window**: 
- **Neon Free Tier**: Up to **6 hours** (max 1 GB change history).
- **Neon Launch Plan ($19/mo)**: Default **1 day (24 hours)**, selectable up to **7 days**.
- **Neon Scale Plan ($69/mo)**: Default **1 day (24 hours)**, selectable up to **30 days**.

## Expected Recovery Time

- **From GCS backup**: 10-30 minutes depending on database size
- **From Neon PITR branch**: 2-5 minutes (instant branch creation)
- **Verification time**: Additional 5-10 minutes for smoke tests

## Last Drill Date

**October 26, 2026**: Verification of schema convergence and 100% test migration suite execution completed on isolated Neon test database (`ep-icy-moon-b4njrgcs`). Full baseline row count captured from primary (`ep-fragrant-salad-aybt4nuh`). Full restore drill onto scratch branch ready for user execution at APPROVAL GATE 1.

## Verification Steps

After any restore, perform these smoke tests:

1. **Database connectivity**: Verify application can connect
2. **Authentication**: Test sign-in with existing accounts
3. **Core functionality**:
   - List jobs
   - Send a message
   - Create a job posting
4. **Data integrity**: Compare row counts before/after restore

## Row Count Comparison

After restore, verify these tables have expected row counts:

```sql
SELECT 'users' as table_name, COUNT(*) FROM users
UNION ALL
SELECT 'candidate_profiles', COUNT(*) FROM candidate_profiles
UNION ALL
SELECT 'companies', COUNT(*) FROM companies
UNION ALL
SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL
SELECT 'resumes', COUNT(*) FROM resumes
UNION ALL
SELECT 'job_postings', COUNT(*) FROM job_postings
UNION ALL
SELECT 'applications', COUNT(*) FROM applications
UNION ALL
SELECT 'messages', COUNT(*) FROM messages
UNION ALL
SELECT 'file_records', COUNT(*) FROM file_records;
```

## Disaster Recovery Scenarios

### Scenario 1: Accidental Data Deletion

1. Immediately stop the application
2. Create a Neon branch from a timestamp before the deletion
3. Verify data in the branch
4. Either:
   - Promote the branch to primary (if acceptable downtime)
   - Or selectively restore deleted data from the branch

### Scenario 2: Schema Migration Failure

1. Never run migrations on primary without a backup
2. Always run migrations on a Neon branch first
3. If migration fails on primary:
   - Restore from latest pre-migration backup
   - Or revert using a Neon branch

### Scenario 3: Complete Database Corruption

1. Restore from latest GCS backup to a new database
2. Verify data integrity
3. Switch application to new database
4. Investigate root cause

## Security Considerations

- GCS bucket is private and not publicly accessible
- No database credentials stored in backup scripts
- Service account keys should be rotated regularly
- Backup files are encrypted at rest in GCS
- Access logs should be monitored for suspicious activity

## Monitoring

Set up alerts for:
- Failed backup jobs
- Backup file age > 25 hours
- Unexpected GCS access patterns
- Low GCS bucket free space

## Contact

For backup-related issues or questions, contact:
- Database Administrator: [TO BE FILLED]
- DevOps Team: [TO BE FILLED]
