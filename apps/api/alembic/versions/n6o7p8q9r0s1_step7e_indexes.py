"""Step 7E: Add performance indexes based on EXPLAIN analysis and FK coverage.

Revision ID: n6o7p8q9r0s1
Revises: m5n6o7p8q9r0
Create Date: 2026-10-31

These indexes were added after EXPLAIN ANALYZE on hot queries:
- FK columns without indexes to enable efficient joins
- Composite indexes for common WHERE + ORDER BY patterns
- Partial indexes for status filters (to reduce index size)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "n6o7p8q9r0s1"
down_revision = "m5n6o7p8q9r0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create indexes on large tables CONCURRENTLY to avoid locks."""

    # === FK Indexes (mandatory for join performance) ===

    # applications(job_id) - used in hot queries for job applications lookup
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_applications_job_id "
        "ON applications(job_id)"
    )

    # applications(candidate_id) - used for my_applications lookup
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_applications_candidate_id "
        "ON applications(candidate_id)"
    )

    # messages(conversation_id) - used for thread message lookup
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_messages_conversation_id "
        "ON messages(conversation_id)"
    )

    # notifications(user_id) - used for user's notifications lookup
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_user_id "
        "ON notifications(user_id)"
    )

    # resumes(candidate_id) - used for candidate's resumes lookup
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_resumes_candidate_id "
        "ON resumes(candidate_id)"
    )

    # fitment_results(candidate_id) - used for candidate fitment scores
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_fitment_results_candidate_id "
        "ON fitment_results(candidate_id)"
    )

    # fitment_results(job_id) - used for job fitment scores
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_fitment_results_job_id "
        "ON fitment_results(job_id)"
    )

    # === Composite Indexes (WHERE + ORDER BY patterns) ===

    # job_postings(status, created_at DESC) - live jobs browse, high volume query
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_job_postings_status_created "
        "ON job_postings(status, created_at DESC) "
        "WHERE status = 'live'"  # Partial index to reduce size
    )

    # applications(job_id, status) - filter applications by status within a job
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_applications_job_status "
        "ON applications(job_id, status)"
    )

    # applications(candidate_id, applied_at DESC) - candidate's applications, newest first
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_applications_candidate_applied "
        "ON applications(candidate_id, applied_at DESC)"
    )

    # messages(conversation_id, sent_at DESC) - thread messages, newest first
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_messages_conversation_sent "
        "ON messages(conversation_id, sent_at DESC)"
    )

    # notifications(user_id, is_read, created_at DESC) - unread notifications, newest first
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_user_read_created "
        "ON notifications(user_id, is_read, created_at DESC)"
    )

    # === Partial Indexes (status filters) ===

    # job_postings(company_id) WHERE status='live' - active jobs for company
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_job_postings_company_live "
        "ON job_postings(company_id, created_at DESC) "
        "WHERE status = 'live'"
    )

    # applications(status) WHERE status IN ('pending', 'shortlisted') - active applications
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_applications_active_status "
        "ON applications(status) "
        "WHERE status IN ('pending', 'shortlisted')"
    )


def downgrade() -> None:
    """Drop all created indexes."""

    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_applications_job_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_applications_candidate_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_messages_conversation_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_notifications_user_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_resumes_candidate_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_fitment_results_candidate_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_fitment_results_job_id")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_job_postings_status_created")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_applications_job_status")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_applications_candidate_applied")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_messages_conversation_sent")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_notifications_user_read_created")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_job_postings_company_live")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_applications_active_status")
