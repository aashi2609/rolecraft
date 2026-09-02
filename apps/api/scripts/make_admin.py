"""Promote a user to admin. Run from apps/api:

    PYTHONPATH=. python scripts/make_admin.py you@email.com
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

# Ensure apps/api is on path when run as scripts/make_admin.py
_API_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _API_ROOT not in sys.path:
    sys.path.insert(0, _API_ROOT)

load_dotenv(os.path.join(_API_ROOT, ".env"))

import asyncpg
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models import User, UserRole


async def add_admin_to_enum() -> None:
    """Use raw asyncpg to ALTER TYPE outside a transaction block."""
    raw_url = os.environ["DATABASE_URL"]
    dsn = raw_url.replace("postgresql+asyncpg://", "postgresql://")
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


async def make_admin(email: str) -> None:
    await add_admin_to_enum()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User {email} not found.")
            return
        user.role = UserRole.admin
        await db.commit()
        print(f"User {email} is now an admin.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote a user to admin")
    parser.add_argument("email", help="User email to promote")
    args = parser.parse_args()
    asyncio.run(make_admin(args.email))
