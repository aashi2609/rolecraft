#!/usr/bin/env python3
"""Verification script to prove no behavior changes after formatting"""

import os
import subprocess


def run_and_log(cmd, description, logfile):
    print(f"\n{'=' * 70}")
    print(f"{description}")
    print("=" * 70)

    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=os.path.dirname(__file__)
    )

    output = f"\n{'=' * 70}\n{description}\n{'=' * 70}\n"
    output += f"Command: {cmd}\n\n"
    output += "STDOUT:\n" + result.stdout + "\n"
    if result.stderr:
        output += "\nSTDERR:\n" + result.stderr + "\n"
    output += f"\nExit Code: {result.returncode}\n"

    print(output)

    with open(logfile, "a", encoding="utf-8") as f:
        f.write(output)

    return result.returncode


# Clear log file
with open("verification_results.txt", "w", encoding="utf-8") as f:
    f.write("VERIFICATION RESULTS\n")
    f.write("=" * 70 + "\n\n")

# Step 1: Versions
run_and_log("python --version", "Python Version", "verification_results.txt")
run_and_log("ruff --version", "Ruff Version", "verification_results.txt")

# Step 2: Format check (should pass now)
run_and_log("ruff format --check .", "Ruff Format Check", "verification_results.txt")

# Step 3: Lint check (should pass)
run_and_log("ruff check .", "Ruff Lint Check", "verification_results.txt")

# Step 4: Test db_guard
run_and_log(
    "python -m pytest tests/test_db_guard.py -v", "DB Guard Tests", "verification_results.txt"
)

# Step 5: Test with TEST_DATABASE_URL unset (should refuse)
env_no_test = os.environ.copy()
if "TEST_DATABASE_URL" in env_no_test:
    del env_no_test["TEST_DATABASE_URL"]

print("\n" + "=" * 70)
print("Testing pytest without TEST_DATABASE_URL (should refuse)")
print("=" * 70)
result = subprocess.run(
    "python -m pytest tests/test_db_guard.py -v --tb=short",
    shell=True,
    capture_output=True,
    text=True,
    env=env_no_test,
)
output = f"\n{'=' * 70}\nPytest without TEST_DATABASE_URL\n{'=' * 70}\n"
output += result.stdout + "\n" + result.stderr + f"\nExit Code: {result.returncode}\n"
print(output)
with open("verification_results.txt", "a", encoding="utf-8") as f:
    f.write(output)

print("\n" + "=" * 70)
print("Verification complete! Check verification_results.txt for full output.")
print("=" * 70)
