@echo off
echo ========================================
echo Step 1: Python and Ruff Versions
echo ========================================
python --version
ruff --version

echo.
echo ========================================
echo Step 2: Ruff Check Statistics
echo ========================================
ruff check . --statistics

echo.
echo ========================================
echo Step 3: Ruff Format Check
echo ========================================
ruff format --check .

echo.
echo Done!
pause
