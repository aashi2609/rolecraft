"""Generic CRUD service for candidate profile items (education, experience, projects, certifications).

This service provides a reusable pattern for profile item CRUD operations to avoid
code duplication across the candidates router.
"""
from __future__ import annotations

from typing import TypeVar, Type, Generic, Callable, Any
from uuid import UUID
from pydantic import BaseModel

from fastapi import HTTPException
from sqlalchemy import select

T = TypeVar("T")  # The model type (Education, Experience, etc)
CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)
OutSchema = TypeVar("OutSchema", bound=BaseModel)


# Model class name → CandidateProfile relationship attribute
_RELATIONSHIP_BY_MODEL: dict[str, str] = {
    "Education": "education",
    "Certification": "certifications",
    "Experience": "experience",
    "Project": "projects",
}


class ProfileItemService(Generic[T, CreateSchema, UpdateSchema, OutSchema]):
    """Generic service for profile item CRUD operations.
    
    Args:
        model: The SQLAlchemy model class (e.g., Education, Experience)
        create_schema: The Pydantic schema for creating items
        update_schema: The Pydantic schema for updating items
        out_schema: The Pydantic schema for output
        candidate_id_field: The field name that stores the candidate_id (default "candidate_id")
        relationship_attr: Optional override for profile relationship name
    """
    
    def __init__(
        self,
        model: Type[T],
        create_schema: Type[CreateSchema],
        update_schema: Type[UpdateSchema],
        out_schema: Type[OutSchema],
        candidate_id_field: str = "candidate_id",
        relationship_attr: str | None = None,
    ):
        self.model = model
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.out_schema = out_schema
        self.candidate_id_field = candidate_id_field
        self.relationship_attr = relationship_attr or _RELATIONSHIP_BY_MODEL.get(
            model.__name__, model.__name__.lower() + "s"
        )
    
    async def list_items(
        self,
        db,
        candidate_id: UUID,
        profile_loader: Callable | None = None,
    ) -> list[OutSchema]:
        """List all items for a candidate (direct FK query — ownership by candidate_id).
        
        profile_loader is accepted for call-site compatibility but unused; listing always
        filters by candidate_id so we never depend on relationship attribute names.
        """
        del profile_loader  # kept for backward-compatible call sites
        items = await db.execute(
            select(self.model).where(
                getattr(self.model, self.candidate_id_field) == candidate_id
            )
        )
        return [self.out_schema.model_validate(item) for item in items.scalars().all()]
    
    async def create_item(
        self,
        db,
        candidate_id: UUID,
        body: CreateSchema,
    ) -> OutSchema:
        """Create a new item for a candidate.
        
        Args:
            db: Database session
            candidate_id: The candidate's user ID
            body: The create schema data
        
        Returns:
            The created item as OutSchema
        """
        row = self.model(**{self.candidate_id_field: candidate_id, **body.model_dump()})
        db.add(row)
        await db.flush()
        return self.out_schema.model_validate(row)
    
    async def update_item(
        self,
        db,
        item_id: UUID,
        candidate_id: UUID,
        body: UpdateSchema,
    ) -> OutSchema:
        """Update an existing item.
        
        Args:
            db: Database session
            item_id: The item's ID
            candidate_id: The candidate's user ID (for ownership check)
            body: The update schema data
        
        Returns:
            The updated item as OutSchema
        
        Raises:
            HTTPException: If item not found or doesn't belong to candidate
        """
        row = await db.get(self.model, item_id)
        if not row or getattr(row, self.candidate_id_field) != candidate_id:
            raise HTTPException(status_code=404, detail="Not found")
        
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        
        await db.flush()
        return self.out_schema.model_validate(row)
    
    async def delete_item(
        self,
        db,
        item_id: UUID,
        candidate_id: UUID,
    ) -> dict[str, bool]:
        """Delete an item.
        
        Args:
            db: Database session
            item_id: The item's ID
            candidate_id: The candidate's user ID (for ownership check)
        
        Returns:
            {"ok": True}
        
        Raises:
            HTTPException: If item not found or doesn't belong to candidate
        """
        row = await db.get(self.model, item_id)
        if not row or getattr(row, self.candidate_id_field) != candidate_id:
            raise HTTPException(status_code=404, detail="Not found")
        
        await db.delete(row)
        return {"ok": True}
