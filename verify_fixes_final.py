#!/usr/bin/env python3
"""Final verification that all files have valid Python syntax."""
import ast
from pathlib import Path

files_to_check = [
    "apps/api/services/entitlement_service.py",
    "apps/api/services/candidate_search_service.py",
    "apps/api/services/payment_service.py",
    "apps/api/services/ats_scorer.py",
    "apps/api/models/__init__.py",
    "apps/api/routers/auth.py",
    "apps/api/routers/jobs.py",
    "apps/api/core/upload_limits.py",
    "apps/api/scripts/backup_db.py",
    "apps/api/scripts/restore_db.py",
    "apps/api/scripts/make_admin.py",
    "apps/api/alembic/env.py",
    "apps/api/tests/conftest.py",
]

root = Path(__file__).parent / "rolecraft"
all_good = True

for fname in files_to_check:
    fpath = root / fname
    if not fpath.exists():
        print(f"✗ NOT FOUND: {fname}")
        all_good = False
        continue
    
    try:
        with open(fpath) as f:
            ast.parse(f.read())
        print(f"✓ {fname}")
    except SyntaxError as e:
        print(f"✗ {fname}: {e}")
        all_good = False

print()
if all_good:
    print("✅ All files have valid Python syntax!")
    exit(0)
else:
    print("❌ Some files have syntax errors")
    exit(1)
