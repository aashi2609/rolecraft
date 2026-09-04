from uuid import UUID

from fastapi import APIRouter, HTTPException

from core.dependencies import CompanyUser, DbSession
from models import Company
from schemas import CompanyOut, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


def _company_out(company: Company, email: str | None = None) -> CompanyOut:
    data = CompanyOut.model_validate(company)
    data.email = email
    return data


@router.get("/me", response_model=CompanyOut)
async def get_me(user: CompanyUser, db: DbSession):
    company = await db.get(Company, user.id)
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return _company_out(company, user.email)


@router.put("/me", response_model=CompanyOut)
async def update_me(body: CompanyUpdate, user: CompanyUser, db: DbSession):
    company = await db.get(Company, user.id)
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(company, k, v)
    await db.flush()
    return _company_out(company, user.email)


@router.get("/{company_id}", response_model=CompanyOut)
async def get_public(company_id: UUID, db: DbSession):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    # Public profile: omit email
    return _company_out(company, email=None)
