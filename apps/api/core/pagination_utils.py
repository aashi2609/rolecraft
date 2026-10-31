"""Pagination helper functions."""

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate_query(
    session: AsyncSession,
    stmt: Any,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Any], int]:
    """
    Execute paginated query and return items + total count.

    Args:
        session: AsyncSession
        stmt: SQLAlchemy select statement (should include WHERE, ORDER BY)
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        (items, total) tuple
    """
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.froms[0] if stmt.froms else stmt)
    if stmt.whereclause is not None:
        count_stmt = count_stmt.where(stmt.whereclause)
    total = await session.scalar(count_stmt) or 0

    # Paginate
    offset = (page - 1) * page_size
    result = await session.execute(stmt.limit(page_size).offset(offset))
    items = result.scalars().unique().all()

    return items, total


async def cursor_paginate_query(
    session: AsyncSession,
    stmt: Any,
    cursor: Optional[str] = None,
    page_size: int = 20,
) -> tuple[list[Any], bool, Optional[str]]:
    """
    Execute keyset (cursor) pagination for unbounded data.

    Args:
        session: AsyncSession
        stmt: SQLAlchemy select statement (should have ORDER BY in DESC order)
        cursor: Cursor string from previous response
        page_size: Items per page

    Returns:
        (items, has_next, next_cursor) tuple
    """
    # Fetch page_size + 1 to detect has_next
    result = await session.execute(stmt.limit(page_size + 1))
    all_items = result.scalars().unique().all()

    has_next = len(all_items) > page_size
    items = all_items[:page_size]

    # Build next cursor from last item
    next_cursor = None
    if has_next and items:
        last_item = items[-1]
        # Cursor format: "id" (use item's string representation or specific field)
        next_cursor = str(last_item.id) if hasattr(last_item, "id") else str(last_item)

    return items, has_next, next_cursor
