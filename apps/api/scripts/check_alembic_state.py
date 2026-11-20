#!/usr/bin/env python
"""Read-only: print alembic version + subscription indexes for DATABASE_URL.

Usage (PowerShell):
    $env:DATABASE_URL = "postgresql://..."
    .venv311/Scripts/python.exe scripts/check_alembic_state.py

Uses core.database.engine so Neon ssl/pooler normalization applies.
Read-only: only SELECTs.
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

api_root = str(Path(__file__).resolve().parent.parent)
if api_root not in sys.path:
    sys.path.insert(0, api_root)

from sqlalchemy import text

from core.database import engine


async def main() -> None:
    async with engine.connect() as c:
        ver = (await c.execute(text("select version_num from alembic_version"))).all()
        print("alembic_version:", [r[0] for r in ver])
        idx = (
            await c.execute(
                text(
                    "select indexname, indexdef from pg_indexes "
                    "where tablename='subscriptions' order by indexname"
                )
            )
        ).all()
        for name, defn in idx:
            print(f"  {name}: {defn}")
        # duplicate live rows (must be 0 before the unique index can apply)
        dup = (
            await c.execute(
                text(
                    "select user_id, count(*) c from subscriptions "
                    "where status::text in ('pending','active') "
                    "group by user_id having count(*) > 1"
                )
            )
        ).all()
        print("users_with_multiple_live_rows:", len(dup))
        for u, c in dup[:10]:
            print(f"  {u}: {c} live rows")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
