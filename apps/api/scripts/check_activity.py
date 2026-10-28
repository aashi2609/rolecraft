import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.database import asyncpg_engine_kwargs

TEST_URL = "postgresql://neondb_owner:npg_7kYhuUif3cRL@ep-icy-moon-b4njrgcs-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

async def check_activity():
    db_url, connect_args = asyncpg_engine_kwargs(TEST_URL)
    engine = create_async_engine(db_url, connect_args=connect_args)
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT pid, state, wait_event_type, wait_event, query, query_start
            FROM pg_stat_activity
            WHERE datname = 'neondb' AND pid <> pg_backend_pid();
        """))
        rows = res.fetchall()
        print(f"Active connections: {len(rows)}")
        for r in rows:
            print(f"PID: {r[0]}, State: {r[1]}, Wait: {r[2]}/{r[3]}, Query: {r[4][:100] if r[4] else ''}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_activity())
