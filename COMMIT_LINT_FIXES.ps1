# Clean commit script - only necessary backend fixes

cd d:\rolecraft\rolecraft

# Reset any previous staging
git reset HEAD .

# Stage ONLY the fixed backend files (17 total)
$files = @(
    "apps/api/services/entitlement_service.py",
    "apps/api/models/__init__.py",
    "apps/api/alembic/env.py",
    "apps/api/scripts/make_admin.py",
    "apps/api/routers/auth.py",
    "apps/api/routers/jobs.py",
    "apps/api/services/payment_service.py",
    "apps/api/services/candidate_search_service.py",
    "apps/api/services/ats_scorer.py",
    "apps/api/core/upload_limits.py",
    "apps/api/scripts/backup_db.py",
    "apps/api/scripts/restore_db.py",
    "apps/api/tests/conftest.py",
    "apps/api/tests/test_schema_validation.py",
    "apps/api/tests/test_resume_backup.py",
    "apps/api/tests/test_rate_limit.py",
    "apps/api/tests/test_fitment_rationale_service.py",
    "apps/api/tests/test_embedding_service.py",
    "apps/api/tests/test_analytics_service.py",
    "apps/api/tests/security/test_jwt_secret_validation.py"
)

Write-Host "Staging only necessary backend fix files..." -ForegroundColor Green

foreach ($file in $files) {
    git add $file
    Write-Host "✓ $file"
}

Write-Host ""
Write-Host "Staged files:" -ForegroundColor Cyan
git diff --cached --name-only

Write-Host ""
Write-Host "Ready to commit. Run:" -ForegroundColor Yellow
Write-Host 'git commit -m "fix 21 backend lint errors: E402 import ordering, E722 bare except, E712/E711 SQLAlchemy comparisons, F841 unused vars"'
Write-Host ""
