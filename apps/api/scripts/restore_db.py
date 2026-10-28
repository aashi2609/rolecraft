#!/usr/bin/env python3
"""
Database restore script for RoleCraft.

Restores a PostgreSQL database from a GCS backup file.

Environment variables required:
- DATABASE_URL: PostgreSQL connection string
- GCS_BACKUP_BUCKET: GCS bucket name where backups are stored
- BACKUP_FILENAME: Specific backup file to restore (or uses latest if not specified)
- GOOGLE_APPLICATION_CREDENTIALS: Path to GCS service account key file (optional if using ADC)

Usage:
    python scripts/restore_db.py [backup_filename]
"""

import os
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def list_backups(bucket_name: str) -> list[str]:
    """List available backups in GCS bucket."""
    cmd = [
        "gsutil",
        "ls",
        f"gs://{bucket_name}/rolecraft_backup_*.sql.gz",
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        backups = result.stdout.strip().split("\n")
        return [b.split("/")[-1] for b in backups if b]
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Could not list backups: {e.stderr}")
        return []


def download_from_gcs(bucket_name: str, remote_name: str, local_file: Path) -> bool:
    """Download backup file from GCS."""
    print(f"Downloading from gs://{bucket_name}/{remote_name}...")

    cmd = [
        "gsutil",
        "cp",
        f"gs://{bucket_name}/{remote_name}",
        str(local_file),
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        print("Download completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: gsutil download failed: {e.stderr}")
        return False


def convert_asyncpg_to_psycopg2(url: str) -> str:
    """Convert asyncpg URL to psycopg2-compatible URL for pg_restore."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def run_pg_restore(database_url: str, backup_file: Path) -> bool:
    """Run pg_restore to restore the database."""
    print(f"Restoring from {backup_file}...")

    # Convert URL for pg_restore
    pg_url = convert_asyncpg_to_psycopg2(database_url)

    # Remove sslmode from URL
    if "?sslmode=" in pg_url:
        pg_url = pg_url.split("?")[0]

    cmd = [
        "pg_restore",
        "-d", pg_url,
        "-F", "c",  # custom format
        "--clean",  # drop existing database objects
        "--if-exists",  # don't error if objects don't exist
        str(backup_file),
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        print("Restore completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: pg_restore failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print("ERROR: pg_restore not found. Please install PostgreSQL client tools.")
        return False


def cleanup_local_file(local_file: Path) -> None:
    """Remove local backup file after restore."""
    try:
        local_file.unlink()
        print(f"Cleaned up local file: {local_file}")
    except OSError as e:
        print(f"WARNING: Could not delete local file {local_file}: {e}")


def main() -> int:
    """Main restore function."""
    # Get environment variables
    database_url = os.getenv("DATABASE_URL")
    bucket_name = os.getenv("GCS_BACKUP_BUCKET")
    backup_filename = os.getenv("BACKUP_FILENAME")

    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return 1

    if not bucket_name:
        print("ERROR: GCS_BACKUP_BUCKET environment variable not set")
        return 1

    # If no specific filename provided, use the latest
    if not backup_filename:
        print("No specific backup file specified, listing available backups...")
        backups = list_backups(bucket_name)
        if not backups:
            print("ERROR: No backups found in bucket")
            return 1
        backup_filename = sorted(backups)[-1]
        print(f"Using latest backup: {backup_filename}")

    # Create temporary local file
    temp_dir = Path("/tmp")
    local_file = temp_dir / backup_filename

    # Download from GCS
    if not download_from_gcs(bucket_name, backup_filename, local_file):
        return 1

    # Confirm restore
    print(f"\nWARNING: This will restore the database from {backup_filename}")
    print("All existing data will be replaced!")
    response = input("Type 'yes' to confirm: ")
    if response.lower() != "yes":
        print("Restore cancelled")
        cleanup_local_file(local_file)
        return 1

    # Run pg_restore
    if not run_pg_restore(database_url, local_file):
        # Keep local file on failure for manual recovery
        print(f"Backup saved locally at {local_file} (restore failed)")
        return 1

    # Clean up local file
    cleanup_local_file(local_file)

    print(f"Restore completed successfully from {backup_filename}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
