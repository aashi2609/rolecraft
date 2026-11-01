#!/usr/bin/env python3
"""Run syntax checks and ruff linting."""
import py_compile
import sys
import subprocess
import json
from pathlib import Path
from collections import defaultdict

# Check syntax of key files
files_to_check = [
    "services/entitlement_service.py",
    "models/__init__.py",
]

api_root = Path(__file__).parent

print("=" * 80)
print("1. SYNTAX VERIFICATION")
print("=" * 80)

syntax_errors = []
for file in files_to_check:
    fpath = api_root / file
    if not fpath.exists():
        print(f"✗ {file}: File not found")
        syntax_errors.append(f"File not found: {file}")
        continue
    
    try:
        py_compile.compile(str(fpath), doraise=True)
        print(f"✓ {file}: Syntax OK")
    except py_compile.PyCompileError as e:
        print(f"✗ {file}: Syntax Error")
        print(f"  {e}")
        syntax_errors.append(f"{file}: {e}")

print()
print("=" * 80)
print("2. RUFF LINTING CHECK")
print("=" * 80)

# Run ruff check
try:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=str(api_root),
        capture_output=True,
        text=True,
        timeout=60
    )
    
    ruff_output = result.stdout + result.stderr
    print(ruff_output)
    
    # Parse errors from output
    error_lines = [line for line in ruff_output.split('\n') if line.strip() and ':' in line]
    
    # Count error types
    error_counts = defaultdict(int)
    error_details = []
    
    for line in error_lines:
        # Parse lines like: "file.py:10:5: E402 ..."
        parts = line.split(':')
        if len(parts) >= 4:
            try:
                error_code = parts[3].strip().split()[0]
                error_counts[error_code] += 1
                error_details.append(line)
            except:
                pass
    
    print()
    print("=" * 80)
    print("3. ERROR SUMMARY")
    print("=" * 80)
    print(f"Total errors found: {len(error_details)}")
    print()
    print("Error types (by frequency):")
    for code, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {code}: {count}")
    
    print()
    print("Top 10 errors:")
    for i, line in enumerate(error_details[:10], 1):
        print(f"  {i}. {line}")
    
    if len(error_details) > 10:
        print(f"  ... and {len(error_details) - 10} more")

except subprocess.TimeoutExpired:
    print("Ruff check timed out")
except Exception as e:
    print(f"Error running ruff: {e}")

print()
print("=" * 80)
print("FINAL REPORT")
print("=" * 80)
if syntax_errors:
    print(f"❌ Syntax errors: {len(syntax_errors)}")
    for err in syntax_errors:
        print(f"   {err}")
else:
    print("✓ No syntax errors in key files")

