from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from core.dependencies import CompanyUser, CurrentUser, DbSession
from models import Company
from schemas import CompanyOut, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CompanyOut)
async def get_me(user: CompanyUser, db: DbSession):
    company = await db.get(Company, user.id)
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return CompanyOut.model_validate(company)


@router.put("/me", response_model=CompanyOut)
async def update_me(body: CompanyUpdate, user: CompanyUser, db: DbSession):
    company = await db.get(Company, user.id)
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(company, k, v)
    await db.flush()
    return CompanyOut.model_validate(company)


@router.get("/{company_id}", response_model=CompanyOut)
async def get_public(company_id: UUID, db: DbSession):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyOut.model_validate(company)
