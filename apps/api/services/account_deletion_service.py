"""Unified user account deletion service.

Handles complete cleanup for candidate and company users:
- Finds and physically deletes all user uploaded files (resumes, photos, marksheets, certificates, logos)
- Deletes user database record (cascading across profiles, items, applications, saved jobs, messages, notifications)
- Used by both self-service user deletion and admin user deletion.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import FileRecord, User
from services.storage_service import delete_stored_file

logger = logging.getLogger(__name__)


async def delete_user_account(db: AsyncSession, user_id: UUID) -> bool:
    """Perform complete cleanup and deletion of a user account.
    
    Returns True if user existed and was deleted, False if user not found.
    """
    user = await db.get(User, user_id)
    if not user:
        return False

    # 1. Collect all stored files associated with this user
    try:
        stmt = select(FileRecord).where(FileRecord.owner_id == user_id)
        result = await db.execute(stmt)
        file_records = result.scalars().all()
        for fr in file_records:
            if fr.storage_path:
                try:
                    delete_stored_file(fr.storage_path)
                except Exception as exc:
                    logger.warning("Failed to delete stored file %s: %s", fr.storage_path, exc)
    except Exception as exc:
        logger.error("Error querying file records for user %s: %s", user_id, exc)

    # 2. Delete user row (cascades to all child rows in DB)
    await db.delete(user)
    await db.flush()
    return True
