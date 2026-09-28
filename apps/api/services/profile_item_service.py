"""Generic CRUD service for candidate profile items (education, experience, projects, certifications).

This service provides a reusable pattern for profile item CRUD operations to avoid
code duplication across the candidates router.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Generic, Type, TypeVar
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update

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

# Models whose changes are resume-relevant (should bump profile_updated_at)
_RESUME_RELEVANT_MODELS: set[str] = {
    "Education",
    "Certification",
    "Experience",
    "Project",
}


async def bump_profile_updated_at(db, candidate_id: UUID) -> None:
    """Centrally bump profile_updated_at for resume-relevant changes.

    Called by ProfileItemService and profile/skills update routes to track
    when the last resume-relevant edit happened.
    """
    from models import CandidateProfile

    await db.execute(
        update(CandidateProfile)
        .where(CandidateProfile.user_id == candidate_id)
        .values(profile_updated_at=datetime.now(timezone.utc))
    )


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
        self.is_resume_relevant = model.__name__ in _RESUME_RELEVANT_MODELS

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
        """Create a new item for a candidate."""
        row = self.model(**{self.candidate_id_field: candidate_id, **body.model_dump()})
        db.add(row)
        await db.flush()
        if self.is_resume_relevant:
            await bump_profile_updated_at(db, candidate_id)
        return self.out_schema.model_validate(row)

    async def update_item(
        self,
        db,
        item_id: UUID,
        candidate_id: UUID,
        body: UpdateSchema,
    ) -> OutSchema:
        """Update an existing item."""
        row = await db.get(self.model, item_id)
        if not row or getattr(row, self.candidate_id_field) != candidate_id:
            raise HTTPException(status_code=404, detail="Not found")

        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(row, k, v)

        await db.flush()
        if self.is_resume_relevant:
            await bump_profile_updated_at(db, candidate_id)
        return self.out_schema.model_validate(row)

    async def delete_item(
        self,
        db,
        item_id: UUID,
        candidate_id: UUID,
    ) -> dict[str, bool]:
        """Delete an item."""
        row = await db.get(self.model, item_id)
        if not row or getattr(row, self.candidate_id_field) != candidate_id:
            raise HTTPException(status_code=404, detail="Not found")

        await db.delete(row)
        if self.is_resume_relevant:
            await bump_profile_updated_at(db, candidate_id)
        return {"ok": True}
