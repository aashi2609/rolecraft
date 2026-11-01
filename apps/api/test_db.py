import asyncio

from sqlalchemy import select

from core.database import AsyncSessionLocal
from models import Company


async def get_companies():
    async with AsyncSessionLocal() as db:
        companies = (await db.execute(select(Company))).scalars().all()
        for c in companies:
            print(f"ID: {c.user_id}, Name: '{c.name}'")


asyncio.run(get_companies())
