"""Candidate search service with composable filters."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, and_, select
from sqlalchemy.orm import selectinload

from models import CandidateProfile, CandidateSkill, Education, Experience, Skill, User
from schemas import CandidateSearchOut
from services.fitment_rationale_service import template_rationale


def apply_keyword_filter(query, q: Optional[str]):
    """Apply general keyword search filter."""
    if not q:
        return query
    
    q_pattern = f"%{q.lower()}%"
    query = query.outerjoin(User, CandidateProfile.user_id == User.id).outerjoin(
        Experience, CandidateProfile.user_id == Experience.candidate_id
    )
    q_skill_subq = (
        select(CandidateSkill.candidate_id)
        .join(Skill, CandidateSkill.skill_id == Skill.id)
        .where(Skill.name.ilike(q_pattern))
    )
    return query.where(
        or_(
            User.email.ilike(q_pattern),
            Experience.role.ilike(q_pattern),
            Experience.designation.ilike(q_pattern),
            CandidateProfile.career_level.ilike(q_pattern),
            CandidateProfile.user_id.in_(q_skill_subq),
        )
    )


def apply_location_filter(query, location: Optional[str]):
    """Match present_address or preferred_locations (comma-separated OR)."""
    if not location:
        return query
    parts = [p.strip() for p in location.split(",") if p.strip()]
    if not parts:
        return query
    loc_conditions = []
    for part in parts:
        pattern = f"%{part.lower()}%"
        loc_conditions.append(CandidateProfile.present_address.ilike(pattern))
        loc_conditions.append(CandidateProfile.permanent_address.ilike(pattern))
        # preferred_locations is ARRAY(String) — cast to text for ilike
        loc_conditions.append(
            func.array_to_string(CandidateProfile.preferred_locations, ",").ilike(pattern)
        )
    return query.where(or_(*loc_conditions))


def apply_skills_filter(query, skills: Optional[str]):
    """Apply skills filter (requires at least one specified skill)."""
    if not skills:
        return query
    
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
        return query.where(CandidateProfile.user_id.in_(skills_union))
    return query


def apply_experience_filter(query, experience_min: Optional[int], experience_max: Optional[int]):
    """Apply experience range filter (checks career_level)."""
    if experience_min is None and experience_max is None:
        return query
    
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
        return query.where(or_(*exp_conditions))
    return query


def apply_education_filter(query, education: Optional[str]):
    """Apply education filter."""
    if not education:
        return query
    
    query = query.outerjoin(Education, CandidateProfile.user_id == Education.candidate_id)
    education_lower = f"%{education.lower()}%"
    return query.where(
        or_(
            Education.qualification_level.ilike(education_lower),
            Education.degree.ilike(education_lower),
            Education.field_of_study.ilike(education_lower),
        )
    )


def apply_title_filter(query, title: Optional[str]):
    """Apply title/role filter (from experience)."""
    if not title:
        return query
    
    query = query.outerjoin(Experience, CandidateProfile.user_id == Experience.candidate_id)
    title_lower = f"%{title.lower()}%"
    return query.where(
        or_(
            Experience.role.ilike(title_lower),
            Experience.designation.ilike(title_lower),
        )
    )


def calculate_experience_years(experience_list) -> int:
    """Calculate total experience years from experience entries."""
    if not experience_list:
        return 0
    
    latest_exp = max(experience_list, key=lambda e: e.from_date or "", default=None)
    if not latest_exp or not latest_exp.from_date:
        return 0
    
    end_date = latest_exp.to_date if latest_exp.to_date else datetime.now()
    start_date = latest_exp.from_date
    
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except:
            return 0
    if isinstance(end_date, str):
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except:
            end_date = datetime.now()
    
    if start_date and end_date:
        return (end_date - start_date).days // 365
    return 0


def get_job_title(experience_list) -> Optional[str]:
    """Get latest job title from experience entries."""
    if not experience_list:
        return None
    
    latest_exp = max(experience_list, key=lambda e: e.from_date or "", default=None)
    if latest_exp:
        return latest_exp.role or latest_exp.designation
    return None


def get_education_level(education_list) -> Optional[str]:
    """Get highest education level from education entries."""
    if not education_list:
        return None
    
    latest_edu = max(education_list, key=lambda e: e.passing_year or 0, default=None)
    if latest_edu:
        return latest_edu.qualification_level or latest_edu.degree
    return None


def parse_expected_salary(experience_list) -> Optional[int]:
    """Parse expected salary from experience entries."""
    if not experience_list:
        return None
    
    for exp in experience_list:
        if exp.expected_salary:
            try:
                # Extract number from salary string like "8-12 LPA" or "8 LPA"
                salary_match = re.search(r'\d+', exp.expected_salary)
                if salary_match:
                    return int(salary_match.group())
            except:
                pass
    return None


def calculate_match_score(skill_names: list, exp_years: int) -> float:
    """Calculate match score (simplified - in production use fitment service)."""
    match_score = 70.0  # Base score
    if skill_names:
        match_score += min(20, len(skill_names) * 2)  # Up to 20 points for skills
    if exp_years > 0:
        match_score += min(10, exp_years)  # Up to 10 points for experience
    return min(98.0, match_score)  # Cap at 98


def transform_profile_to_search_out(profile: CandidateProfile, salary_min: Optional[int], salary_max: Optional[int]) -> Optional[CandidateSearchOut]:
    """Transform a CandidateProfile to CandidateSearchOut with salary filtering."""
    exp_years = calculate_experience_years(profile.experience)
    skill_names = [cs.skill.name for cs in profile.skills if cs.skill]
    job_title = get_job_title(profile.experience)
    education_level = get_education_level(profile.education)
    expected_salary = parse_expected_salary(profile.experience)
    
    # Apply salary filters after parsing
    if salary_min is not None and expected_salary is not None:
        if expected_salary < salary_min:
            return None
    if salary_max is not None and expected_salary is not None:
        if expected_salary > salary_max:
            return None
    
    match_score = calculate_match_score(skill_names, exp_years)
    rationale = template_rationale(skill_names, skill_names)

    return CandidateSearchOut(
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
        rationale=rationale,
        rationale_source="template",
    )


async def search_candidates(
    db,
    q: Optional[str] = None,
    location: Optional[str] = None,
    skills: Optional[str] = None,
    experience_min: Optional[int] = None,
    experience_max: Optional[int] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    education: Optional[str] = None,
    title: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CandidateSearchOut], int]:
    """
    Search candidates with advanced filtering and pagination.
    Returns (candidates, total_count).
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
    
    # Apply filters in sequence
    query = apply_keyword_filter(query, q)
    query = apply_location_filter(query, location)
    query = apply_skills_filter(query, skills)
    query = apply_experience_filter(query, experience_min, experience_max)
    query = apply_education_filter(query, education)
    query = apply_title_filter(query, title)
    
    # Use distinct to avoid duplicate profiles from outer joins
    query = query.distinct()
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    profiles = result.scalars().all()
    
    # Transform to output format with salary filtering
    candidates = []
    for profile in profiles:
        candidate_out = transform_profile_to_search_out(profile, salary_min, salary_max)
        if candidate_out:
            candidates.append(candidate_out)
    
    return candidates, total_count
