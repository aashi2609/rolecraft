import asyncio
from core.database import AsyncSessionLocal
from sqlalchemy import update
from models import Company

async def fix():
    async with AsyncSessionLocal() as db:
        await db.execute(update(Company).values(name='TechNova Inc.'))
        await db.commit()

asyncio.run(fix())
