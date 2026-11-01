# Step-by-step ruff fix application

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Applying Ruff Fixes" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Show current errors
Write-Host "`n=== Current Errors ===" -ForegroundColor Yellow
ruff check . --statistics

# Apply safe fixes
Write-Host "`n=== Applying Safe Fixes ===" -ForegroundColor Yellow
ruff check --fix .

# Show remaining errors
Write-Host "`n=== Remaining Errors ===" -ForegroundColor Yellow
ruff check . --statistics

# Show what changed
Write-Host "`n=== Git Diff ===" -ForegroundColor Yellow
git diff --stat

Write-Host "`n=== REVIEW CHANGES ===" -ForegroundColor Magenta
Write-Host "Run: git diff" -ForegroundColor Magenta
Write-Host "Check for removed imports that are needed for side effects" -ForegroundColor Magenta
Write-Host "Add '# noqa: F401' comments where needed" -ForegroundColor Magenta

Write-Host "`n=== Next Steps ===" -ForegroundColor Green
Write-Host "1. Review: git diff" -ForegroundColor White
Write-Host "2. Format: ruff format ." -ForegroundColor White
Write-Host "3. Commit fixes: git commit -am 'fix: resolve ruff lint errors'" -ForegroundColor White
Write-Host "4. Commit format: git commit -am 'style: apply ruff formatting'" -ForegroundColor White
