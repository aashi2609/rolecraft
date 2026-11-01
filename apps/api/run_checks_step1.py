#!/usr/bin/env python3
"""Step 1: Check versions and run ruff checks"""
import subprocess


def run_command(cmd, description):
    print(f"\n{'='*60}")
    print(f"{description}")
    print('='*60)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"Exit code: {result.returncode}")
    return result.returncode

# Step 1a: Check versions
run_command("python --version", "Python Version")
run_command("ruff --version", "Ruff Version")

# Step 1b: Ruff check with statistics
run_command("ruff check . --statistics", "Ruff Check Statistics")

# Step 1c: Ruff format check
run_command("ruff format --check .", "Ruff Format Check")

print("\n" + "="*60)
print("Checks complete! Review output above.")
print("="*60)
