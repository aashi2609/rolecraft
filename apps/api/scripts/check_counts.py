"""Check row counts on Primary DB and Test DB."""
import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.database import asyncpg_engine_kwargs


PRIMARY_URL = os.getenv("PRIMARY_DATABASE_URL")
TEST_URL = os.getenv("TEST_DATABASE_URL")

if not PRIMARY_URL:
    print("ERROR: PRIMARY_DATABASE_URL environment variable not set", file=sys.stderr)
    sys.exit(1)
if not TEST_URL:
    print("ERROR: TEST_DATABASE_URL environment variable not set", file=sys.stderr)
    sys.exit(1)

TABLES = ["users", "resumes", "subscriptions", "file_records", "job_postings"]

async def get_counts(url: str, label: str):
    print(f"\n--- Checking {label} ---")
    db_url, connect_args = asyncpg_engine_kwargs(url)
    engine = create_async_engine(db_url, connect_args=connect_args)
    counts = {}
    async with engine.connect() as conn:
        for t in TABLES:
            try:
                cnt = (await conn.execute(text(f"SELECT COUNT(*) FROM {t};"))).scalar()
                counts[t] = cnt
                print(f"  {t}: {cnt}")
            except Exception as e:
                counts[t] = f"error/missing ({e.__class__.__name__})"
                print(f"  {t}: {counts[t]}")
    await engine.dispose()
    return counts

async def main():
    print(f"Python: {sys.version}")
    print(f"PWD: {os.getcwd()}")
    await get_counts(PRIMARY_URL, "PRIMARY DATABASE")
    await get_counts(TEST_URL, "TEST DATABASE")

if __name__ == "__main__":
    asyncio.run(main())
