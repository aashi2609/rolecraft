import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    db_url = os.environ.get("DATABASE_URL")
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
    print(f"Connecting to {db_url}...")
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'resume_builder';")
        await conn.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'job_search';")
        await conn.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'complete';")
        await conn.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'corporate_annual';")
        await conn.execute("ALTER TYPE plan_tier ADD VALUE IF NOT EXISTS 'corporate_lifetime';")
        print("Successfully added new values to plan_tier ENUM.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
