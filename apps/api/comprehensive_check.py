#!/usr/bin/env python3
"""Comprehensive lint and syntax check."""
import os
import sys
import ast
import re
from pathlib import Path
from collections import defaultdict

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 90)
print("COMPREHENSIVE LINT AND SYNTAX CHECK")
print("=" * 90)

# ─────────────────────────────────────────────────────────────────────────────
# Part 1: Syntax Check
# ─────────────────────────────────────────────────────────────────────────────

print("\n1. SYNTAX VERIFICATION FOR KEY FILES")
print("-" * 90)

files_to_check = [
    "services/entitlement_service.py",
    "models/__init__.py",
]

api_root = Path(__file__).parent
syntax_errors = []

for file in files_to_check:
    fpath = api_root / file
    if not fpath.exists():
        print(f"✗ {file}: File not found")
        syntax_errors.append(f"File not found: {file}")
        continue
    
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        print(f"✓ {file}: Syntax valid")
    except SyntaxError as e:
        print(f"✗ {file}: Syntax error at line {e.lineno}: {e.msg}")
        syntax_errors.append(f"{file}:{e.lineno}: {e.msg}")
    except Exception as e:
        print(f"✗ {file}: Error: {e}")
        syntax_errors.append(f"{file}: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Part 2: Basic Lint Pattern Analysis
# ─────────────────────────────────────────────────────────────────────────────

print("\n2. LINT PATTERN ANALYSIS")
print("-" * 90)

# Patterns to check
patterns = {
    'E402': (r'^\s+(import|from)\s+', 'Module level import not at top'),
    'F841': (r'\w+\s*=\s*(?!.*return|\.\.).*$', 'Local variable assigned but never used'),
    'E711': (r'\s+(==|!=)\s+(True|False|None)', 'Comparison to True, False or None'),
    'E712': (r'\s+(==|!=)\s+True|False', 'True/False comparison'),
    'E722': (r'except:\s*$', 'Bare except'),
    'F821': (r'\b(?<![\w\.])(?![_\w]*\w_)[A-Z][a-z]+(?=\()', 'Undefined name'),
}

error_counts = defaultdict(int)
error_details = []

# Scan all Python files in API directory
for py_file in api_root.rglob('*.py'):
    # Skip common directories
    if any(part in str(py_file) for part in ['__pycache__', '.git', 'venv', '.venv']):
        continue
    
    try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Check each line
        for line_num, line in enumerate(lines, 1):
            # E402: Module level imports not at top
            if re.match(r'^\s+(import|from)\s+', line):
                # But allow in functions, classes, except blocks
                if line_num > 1:
                    # Simple heuristic: if line is indented and previous lines suggest we're in a function
                    error_counts['E402'] += 1
                    rel_path = py_file.relative_to(api_root)
                    error_details.append(f"{rel_path}:{line_num}: E402 {line.strip()[:60]}")
            
            # E722: Bare except
            if re.search(r'except\s*:\s*$', line):
                error_counts['E722'] += 1
                rel_path = py_file.relative_to(api_root)
                error_details.append(f"{rel_path}:{line_num}: E722 Bare except")
            
            # E711: Comparison to None
            if re.search(r'\s+(==|!=)\s+None\b', line) and 'is' not in line:
                error_counts['E711'] += 1
                rel_path = py_file.relative_to(api_root)
                error_details.append(f"{rel_path}:{line_num}: E711 {line.strip()[:60]}")
            
            # E712: True/False comparison
            if re.search(r'\s+(==|!=)\s+(True|False)\b', line):
                error_counts['E712'] += 1
                rel_path = py_file.relative_to(api_root)
                error_details.append(f"{rel_path}:{line_num}: E712 {line.strip()[:60]}")
    
    except Exception as e:
        pass

print(f"\nTotal patterns detected: {len(error_details)}")
print("\nError type summary:")
for code in sorted(error_counts.keys()):
    print(f"  {code}: {error_counts[code]}")

print("\nTop 20 error instances:")
for i, err in enumerate(error_details[:20], 1):
    print(f"  {i}. {err}")

if len(error_details) > 20:
    print(f"  ... and {len(error_details) - 20} more")

# ─────────────────────────────────────────────────────────────────────────────
# Part 3: Summary
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 90)
print("FINAL REPORT")
print("=" * 90)

if syntax_errors:
    print(f"\n❌ Syntax errors found: {len(syntax_errors)}")
    for err in syntax_errors:
        print(f"   {err}")
else:
    print(f"\n✓ No syntax errors in key files (services/entitlement_service.py, models/__init__.py)")

print(f"\nBasic lint pattern issues detected: {len(error_details)}")
if error_counts:
    print("Major error types:")
    for code, count in sorted(error_counts.items(), key=lambda x: -x[1]):
        print(f"  - {code}: {count}")

