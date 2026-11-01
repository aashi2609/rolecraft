"""Pagination response schemas."""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response for offset-based pagination."""

    items: list[T]
    total: int = Field(..., description="Total number of items matching the query")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    has_more: bool = Field(
        ..., description="True if there are more pages after this one"
    )


class CursorResponse(BaseModel, Generic[T]):
    """Keyset (cursor) pagination for unbounded data like messages/notifications."""

    items: list[T]
    has_next: bool = Field(..., description="True if more items exist")
    cursor: Optional[str] = Field(
        None, description="Cursor for next page (if has_next=true)"
    )
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
