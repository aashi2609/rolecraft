from uuid import UUID
import uuid as uuid_mod
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, select, or_, and_, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from core.dependencies import CandidateUser, CurrentUser, DbSession
from models import (
    CandidateProfile,
    CandidateSkill,
    Certification,
    Education,
    Experience,
    Project,
    Skill,
    User,
)
from schemas import (
    CandidateProfileOut,
    CandidateProfileUpdate,
    CandidateSearchOut,
    CertificationIn,
    CertificationOut,
    EducationIn,
    EducationOut,
    ExperienceIn,
    ExperienceOut,
    ProjectIn,
    ProjectOut,
    SkillsUpdate,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


async def _load_profile(db, user_id: UUID) -> CandidateProfile:
    result = await db.execute(
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.certifications),
            selectinload(CandidateProfile.experience),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
            selectinload(CandidateProfile.user),
        )
        .where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return profile


def _profile_meta(profile: CandidateProfile) -> tuple[Optional[str], dict[str, bool]]:
    links = profile.weblinks or {}
    display_name = links.get("display_name")
    prefs = links.get("notification_prefs") or {}
    if isinstance(prefs, dict):
        return display_name, {k: bool(v) for k, v in prefs.items()}
    return display_name, {}


def _to_out(profile: CandidateProfile) -> CandidateProfileOut:
    full_name, notification_prefs = _profile_meta(profile)
    return CandidateProfileOut(
        user_id=profile.user_id,
        email=profile.user.email if profile.user else None,
        full_name=full_name,
        photo_url=profile.photo_url,
        career_level=profile.career_level,
        dob=profile.dob,
        gender=profile.gender,
        marital_status=profile.marital_status,
        present_address=profile.present_address,
        permanent_address=profile.permanent_address,
        preferred_locations=profile.preferred_locations or [],
        preferred_sectors=profile.preferred_sectors or [],
        strengths=profile.strengths or [],
        weaknesses=profile.weaknesses or [],
        weblinks=profile.weblinks or {},
        notification_prefs=notification_prefs,
        annual_family_income=profile.annual_family_income,
        skills=[cs.skill.name for cs in profile.skills if cs.skill],
        education=[EducationOut.model_validate(e) for e in profile.education],
        certifications=[CertificationOut.model_validate(c) for c in profile.certifications],
        experience=[ExperienceOut.model_validate(e) for e in profile.experience],
        projects=[ProjectOut.model_validate(p) for p in profile.projects],
    )


@router.get("/me", response_model=CandidateProfileOut)
async def get_me(user: CandidateUser, db: DbSession):
    return _to_out(await _load_profile(db, user.id))


@router.put("/me", response_model=CandidateProfileOut)
async def update_me(body: CandidateProfileUpdate, user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    data = body.model_dump(exclude_unset=True)
    links = dict(profile.weblinks or {})
    if "full_name" in data:
        links["display_name"] = data.pop("full_name")
    if "notification_prefs" in data:
        links["notification_prefs"] = data.pop("notification_prefs")
    profile.weblinks = links
    for k, v in data.items():
        setattr(profile, k, v)
    await db.flush()
    return _to_out(await _load_profile(db, user.id))


# Education
@router.get("/me/education", response_model=list[EducationOut])
async def list_education(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return [EducationOut.model_validate(e) for e in profile.education]


@router.post("/me/education", response_model=EducationOut)
async def add_education(body: EducationIn, user: CandidateUser, db: DbSession):
    row = Education(candidate_id=user.id, **body.model_dump())
    db.add(row)
    await db.flush()
    return EducationOut.model_validate(row)


@router.put("/me/education/{item_id}", response_model=EducationOut)
async def update_education(item_id: UUID, body: EducationIn, user: CandidateUser, db: DbSession):
    row = await db.get(Education, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    return EducationOut.model_validate(row)


@router.delete("/me/education/{item_id}")
async def delete_education(item_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Education, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    return {"ok": True}


# Certifications
@router.get("/me/certifications", response_model=list[CertificationOut])
async def list_certs(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return [CertificationOut.model_validate(c) for c in profile.certifications]


@router.post("/me/certifications", response_model=CertificationOut)
async def add_cert(body: CertificationIn, user: CandidateUser, db: DbSession):
    row = Certification(candidate_id=user.id, **body.model_dump())
    db.add(row)
    await db.flush()
    return CertificationOut.model_validate(row)


@router.put("/me/certifications/{item_id}", response_model=CertificationOut)
async def update_cert(item_id: UUID, body: CertificationIn, user: CandidateUser, db: DbSession):
    row = await db.get(Certification, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    return CertificationOut.model_validate(row)


@router.delete("/me/certifications/{item_id}")
async def delete_cert(item_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Certification, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    return {"ok": True}


# Experience
@router.get("/me/experience", response_model=list[ExperienceOut])
async def list_exp(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return [ExperienceOut.model_validate(e) for e in profile.experience]


@router.post("/me/experience", response_model=ExperienceOut)
async def add_exp(body: ExperienceIn, user: CandidateUser, db: DbSession):
    row = Experience(candidate_id=user.id, **body.model_dump())
    db.add(row)
    await db.flush()
    return ExperienceOut.model_validate(row)


@router.put("/me/experience/{item_id}", response_model=ExperienceOut)
async def update_exp(item_id: UUID, body: ExperienceIn, user: CandidateUser, db: DbSession):
    row = await db.get(Experience, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    return ExperienceOut.model_validate(row)


@router.delete("/me/experience/{item_id}")
async def delete_exp(item_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Experience, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    return {"ok": True}


# Projects
@router.get("/me/projects", response_model=list[ProjectOut])
async def list_projects(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return [ProjectOut.model_validate(p) for p in profile.projects]


@router.post("/me/projects", response_model=ProjectOut)
async def add_project(body: ProjectIn, user: CandidateUser, db: DbSession):
    row = Project(candidate_id=user.id, **body.model_dump())
    db.add(row)
    await db.flush()
    return ProjectOut.model_validate(row)


@router.put("/me/projects/{item_id}", response_model=ProjectOut)
async def update_project(item_id: UUID, body: ProjectIn, user: CandidateUser, db: DbSession):
    row = await db.get(Project, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.flush()
    return ProjectOut.model_validate(row)


@router.delete("/me/projects/{item_id}")
async def delete_project(item_id: UUID, user: CandidateUser, db: DbSession):
    row = await db.get(Project, item_id)
    if not row or row.candidate_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    return {"ok": True}


# Skills
@router.get("/me/skills")
async def get_skills(user: CandidateUser, db: DbSession):
    profile = await _load_profile(db, user.id)
    return {"skills": [cs.skill.name for cs in profile.skills if cs.skill]}


@router.put("/me/skills")
async def put_skills(body: SkillsUpdate, user: CandidateUser, db: DbSession):
    unique_names: list[str] = []
    seen: set[str] = set()
    for raw in body.skills:
        name = raw.strip()
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            unique_names.append(name)

    await db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == user.id))
    await db.flush()

    linked: set[UUID] = set()
    for name in unique_names:
        skill = await db.scalar(select(Skill).where(Skill.name == name))
        if not skill:
            stmt = (
                insert(Skill)
                .values(id=uuid_mod.uuid4(), name=name)
                .on_conflict_do_nothing(index_elements=["name"])
            )
            await db.execute(stmt)
            skill = await db.scalar(select(Skill).where(Skill.name == name))
        if skill and skill.id not in linked:
            db.add(CandidateSkill(candidate_id=user.id, skill_id=skill.id))
            linked.add(skill.id)
    await db.flush()
    return {"skills": unique_names}


# ── Public Candidate Search ─────────────────────────────────────────────────────

@router.get("/search", response_model=list[CandidateSearchOut])
async def search_candidates(
    db: DbSession,
    q: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    skills: Optional[str] = Query(None),
    experience_min: Optional[int] = Query(None),
    experience_max: Optional[int] = Query(None),
    salary_min: Optional[int] = Query(None),
    salary_max: Optional[int] = Query(None),
    education: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Public candidate search endpoint with advanced filtering and pagination.
    This replaces the frontend SEED_CANDIDATES mock data.
    """
    # Build base query with skills preloaded
    query = (
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.skills).selectinload(CandidateSkill.skill),
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.experience),
            selectinload(CandidateProfile.user),
        )
    )
    
    # Apply filters
    conditions = []
    
    # General keyword search (q)
    if q:
        q_pattern = f"%{q.lower()}%"
        query = query.outerjoin(User, CandidateProfile.user_id == User.id).outerjoin(
            Experience, CandidateProfile.user_id == Experience.candidate_id
        )
        q_skill_subq = (
            select(CandidateSkill.candidate_id)
            .join(Skill, CandidateSkill.skill_id == Skill.id)
            .where(Skill.name.ilike(q_pattern))
        )
        conditions.append(
            or_(
                User.email.ilike(q_pattern),
                Experience.role.ilike(q_pattern),
                Experience.designation.ilike(q_pattern),
                CandidateProfile.career_level.ilike(q_pattern),
                CandidateProfile.user_id.in_(q_skill_subq),
            )
        )

    # Location filter (matches present_address)
    if location:
        location_lower = f"%{location.lower()}%"
        conditions.append(CandidateProfile.present_address.ilike(location_lower))
    
    # Skills filter (requires at least one specified skill)
    if skills:
        skill_list = [s.strip().lower() for s in skills.split(",") if s.strip()]
        skill_conditions = []
        for skill_name in skill_list:
            skill_conditions.append(
                select(CandidateSkill.candidate_id)
                .join(Skill, CandidateSkill.skill_id == Skill.id)
                .where(Skill.name.ilike(f"%{skill_name}%"))
            )
        if skill_conditions:
            # Use OR for skills (candidates with at least one matching skill)
            skills_union = skill_conditions[0]
            for sc in skill_conditions[1:]:
                skills_union = skills_union.union(sc)
            conditions.append(CandidateProfile.user_id.in_(skills_union))
    
    # Experience range filter (simplified - checks career_level)
    if experience_min is not None or experience_max is not None:
        exp_conditions = []
        if experience_min is not None:
            if experience_min >= 5:
                exp_conditions.append(CandidateProfile.career_level.in_(["Experienced", "Senior"]))
            elif experience_min >= 3:
                exp_conditions.append(CandidateProfile.career_level.in_(["Mid Career", "Experienced", "Senior"]))
            elif experience_min >= 1:
                exp_conditions.append(CandidateProfile.career_level.in_(["Early Career", "Mid Career", "Experienced", "Senior"]))
        if experience_max is not None:
            if experience_max < 1:
                exp_conditions.append(CandidateProfile.career_level == "Fresher")
            elif experience_max < 3:
                exp_conditions.append(CandidateProfile.career_level.in_(["Fresher", "Early Career"]))
        if exp_conditions:
            conditions.append(or_(*exp_conditions))
    
    # Education filter
    if education:
        query = query.outerjoin(Education, CandidateProfile.user_id == Education.candidate_id)
        education_lower = f"%{education.lower()}%"
        conditions.append(
            or_(
                Education.qualification_level.ilike(education_lower),
                Education.degree.ilike(education_lower),
                Education.field_of_study.ilike(education_lower),
            )
        )
    
    # Title/role filter (from experience)
    if title:
        query = query.outerjoin(Experience, CandidateProfile.user_id == Experience.candidate_id)
        title_lower = f"%{title.lower()}%"
        conditions.append(
            or_(
                Experience.role.ilike(title_lower),
                Experience.designation.ilike(title_lower),
            )
        )

    # Use distinct to avoid duplicate profiles from outer joins
    query = query.distinct()
    
    # Apply all conditions
    if conditions:
        query = query.where(and_(*conditions))
    
    # Get total count for pagination
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    profiles = result.scalars().all()
    
    # Transform to output format
    candidates = []
    for profile in profiles:
        # Calculate experience years (simplified)
        exp_years = 0
        if profile.experience:
            latest_exp = max(profile.experience, key=lambda e: e.from_date or "", default=None)
            if latest_exp and latest_exp.from_date:
                from datetime import datetime
                end_date = latest_exp.to_date if latest_exp.to_date else datetime.now()
                start_date = latest_exp.from_date
                if isinstance(start_date, str):
                    try:
                        start_date = datetime.strptime(start_date, "%Y-%m-%d")
                    except:
                        start_date = None
                if isinstance(end_date, str):
                    try:
                        end_date = datetime.strptime(end_date, "%Y-%m-%d")
                    except:
                        end_date = datetime.now()
                if start_date and end_date:
                    exp_years = (end_date - start_date).days // 365
        
        # Get skills
        skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
        
        # Get latest job title
        job_title = None
        if profile.experience:
            latest_exp = max(profile.experience, key=lambda e: e.from_date or "", default=None)
            if latest_exp:
                job_title = latest_exp.role or latest_exp.designation
        
        # Get education level
        education_level = None
        if profile.education:
            latest_edu = max(profile.education, key=lambda e: e.passing_year or 0, default=None)
            if latest_edu:
                education_level = latest_edu.qualification_level or latest_edu.degree
        
        # Parse expected salary (simplified)
        expected_salary = None
        if profile.experience:
            for exp in profile.experience:
                if exp.expected_salary:
                    try:
                        # Extract number from salary string like "8-12 LPA" or "8 LPA"
                        import re
                        salary_match = re.search(r'\d+', exp.expected_salary)
                        if salary_match:
                            expected_salary = int(salary_match.group())
                            break
                    except:
                        pass
        
        # Apply salary filters after parsing
        if salary_min is not None and expected_salary is not None:
            if expected_salary < salary_min:
                continue
        if salary_max is not None and expected_salary is not None:
            if expected_salary > salary_max:
                continue
        
        # Calculate match score (simplified - in production use fitment service)
        match_score = 70.0  # Base score
        if skill_names:
            match_score += min(20, len(skill_names) * 2)  # Up to 20 points for skills
        if exp_years > 0:
            match_score += min(10, exp_years)  # Up to 10 points for experience
        match_score = min(98.0, match_score)  # Cap at 98
        
        candidates.append(
            CandidateSearchOut(
                id=profile.user_id,
                name=profile.user.email.split("@")[0].replace(".", " ").title() if profile.user else None,
                title=job_title,
                experience_years=exp_years if exp_years > 0 else None,
                location=profile.preferred_locations[0] if profile.preferred_locations else profile.present_address,
                skills=skill_names[:10],  # Limit to top 10 skills
                match_percent=round(match_score, 1),
                education=education_level,
                expected_salary_lpa=expected_salary,
                notice_period_days=30,  # Default notice period (can be calculated from gaps)
                photo_url=profile.photo_url,
            )
        )
    
    # Return candidates
    return candidates


@router.get("/{candidate_id}", response_model=CandidateProfileOut)
async def get_candidate_public(candidate_id: UUID, user: CurrentUser, db: DbSession):
    return _to_out(await _load_profile(db, candidate_id))
