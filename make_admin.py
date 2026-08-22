import sys
import os
import argparse
import asyncio
from dotenv import load_dotenv

api_dir = os.path.join(os.path.dirname(__file__), 'apps', 'api')
sys.path.append(api_dir)
load_dotenv(os.path.join(api_dir, '.env'))

import asyncpg
from sqlalchemy import select
from apps.api.core.database import AsyncSessionLocal
from apps.api.models import User, UserRole


async def add_admin_to_enum():
    """Use raw asyncpg to ALTER TYPE outside a transaction block."""
    # Read the raw DATABASE_URL from env and convert to asyncpg-compatible DSN
    raw_url = os.environ["DATABASE_URL"]
    dsn = raw_url.replace("postgresql+asyncpg://", "postgresql://")
    # Strip query params that asyncpg doesn't understand (sslmode, channel_binding)
    if "?" in dsn:
        dsn = dsn.split("?")[0]

    conn = await asyncpg.connect(dsn, ssl="require")
    try:
        result = await conn.fetch(
            "SELECT enumlabel FROM pg_enum WHERE enumtypid = 'user_role'::regtype"
        )
        existing = [row["enumlabel"] for row in result]
        if "admin" not in existing:
            await conn.execute("ALTER TYPE user_role ADD VALUE 'admin'")
            print("Added 'admin' to user_role enum in database.")
        else:
            print("'admin' already exists in user_role enum.")
    finally:
        await conn.close()


async def make_admin(email: str):
    await add_admin_to_enum()

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                print(f"Error: User with email {email} not found.")
                return

            user.role = UserRole.admin
            await db.commit()
            print(f"Success! {email} is now an admin.")
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Make a user an admin.")
    parser.add_argument("email", help="The email address of the user to promote.")
    args = parser.parse_args()
    asyncio.run(make_admin(args.email))
