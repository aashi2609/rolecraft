#!/usr/bin/env python3
"""
Database backup script for RoleCraft.

Backs up the PostgreSQL database to a private GCS bucket using pg_dump.
The backup is compressed and timestamped.

Environment variables required:
- DATABASE_URL: PostgreSQL connection string (must be pg_dump compatible)
- GCS_BACKUP_BUCKET: GCS bucket name for storing backups
- GOOGLE_APPLICATION_CREDENTIALS: Path to GCS service account key file (optional if using ADC)

Usage:
    python scripts/backup_db.py
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def get_backup_filename() -> str:
    """Generate a timestamped backup filename."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"rolecraft_backup_{timestamp}.sql.gz"


def convert_asyncpg_to_psycopg2(url: str) -> str:
    """Convert asyncpg URL to psycopg2-compatible URL for pg_dump."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def run_pg_dump(database_url: str, output_file: Path) -> bool:
    """Run pg_dump to create a compressed backup."""
    print(f"Starting backup to {output_file}...")

    # Convert URL for pg_dump
    pg_url = convert_asyncpg_to_psycopg2(database_url)

    # Remove sslmode from URL (pg_dump handles SSL differently)
    if "?sslmode=" in pg_url:
        pg_url = pg_url.split("?")[0]

    cmd = [
        "pg_dump",
        "-F", "c",  # custom format (compressed, allows selective restore)
        "-f", str(output_file),
        pg_url,
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        print("Backup completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: pg_dump failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print("ERROR: pg_dump not found. Please install PostgreSQL client tools.")
        return False


def upload_to_gcs(local_file: Path, bucket_name: str, remote_name: str) -> bool:
    """Upload backup file to GCS using gsutil."""
    print(f"Uploading to gs://{bucket_name}/{remote_name}...")

    cmd = [
        "gsutil",
        "cp",
        str(local_file),
        f"gs://{bucket_name}/{remote_name}",
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        print("Upload completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: gsutil upload failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print("ERROR: gsutil not found. Please install Google Cloud SDK.")
        return False


def cleanup_local_file(local_file: Path) -> None:
    """Remove local backup file after successful upload."""
    try:
        local_file.unlink()
        print(f"Cleaned up local file: {local_file}")
    except OSError as e:
        print(f"WARNING: Could not delete local file {local_file}: {e}")


def main() -> int:
    """Main backup function."""
    # Get environment variables
    database_url = os.getenv("DATABASE_URL")
    bucket_name = os.getenv("GCS_BACKUP_BUCKET")

    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return 1

    if not bucket_name:
        print("ERROR: GCS_BACKUP_BUCKET environment variable not set")
        return 1

    # Generate backup filename
    backup_filename = get_backup_filename()

    # Create temporary local file (cross-platform)
    import tempfile
    temp_dir = Path(tempfile.gettempdir())
    local_file = temp_dir / backup_filename

    # Run pg_dump
    if not run_pg_dump(database_url, local_file):
        # Clean up on failure
        if local_file.exists():
            local_file.unlink()
        return 1

    # Upload to GCS
    if not upload_to_gcs(local_file, bucket_name, backup_filename):
        # Keep local file on upload failure for manual recovery
        print(f"Backup saved locally at {local_file} (upload failed)")
        return 1

    # Clean up local file
    cleanup_local_file(local_file)

    print(f"Backup completed successfully: gs://{bucket_name}/{backup_filename}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
