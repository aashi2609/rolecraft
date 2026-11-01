# Complete CI verification script
# Run this after activating venv: .venv311\Scripts\activate

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backend CI Verification - All Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Step 1: Versions
Write-Host "`n=== Step 1: Versions ===" -ForegroundColor Yellow
python --version
ruff --version

# Step 2: Ruff Check
Write-Host "`n=== Step 2: Ruff Check ===" -ForegroundColor Yellow
ruff check . --statistics

# Step 3: Ruff Format Check
Write-Host "`n=== Step 3: Ruff Format Check ===" -ForegroundColor Yellow
ruff format --check .

# Step 4: pip check
Write-Host "`n=== Step 4: pip check ===" -ForegroundColor Yellow
pip check

# Step 5: Alembic check
Write-Host "`n=== Step 5: Alembic check ===" -ForegroundColor Yellow
alembic check

# Step 6: pytest
Write-Host "`n=== Step 6: pytest ===" -ForegroundColor Yellow
pytest -v --tb=short

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "All checks complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
