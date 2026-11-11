"""Profile data cleaner — normalises messy candidate data before AI processing."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Optional

from models import CandidateProfile

# Common skill aliases → canonical form
_SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "golang": "Go",
    "go": "Go",
    "react.js": "React",
    "reactjs": "React",
    "react": "React",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "node": "Node.js",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "angular.js": "Angular",
    "angularjs": "Angular",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "aws": "AWS",
    "gcp": "Google Cloud",
    "azure": "Azure",
    "docker": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "dl": "Deep Learning",
    "nlp": "Natural Language Processing",
    "cv": "Computer Vision",
    "html5": "HTML",
    "css3": "CSS",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
    "nosql": "NoSQL",
    "git": "Git",
    "github": "GitHub",
    "figma": "Figma",
    "photoshop": "Photoshop",
    "illustrator": "Illustrator",
    "matlab": "MATLAB",
    "excel": "Excel",
    "powerbi": "Power BI",
    "tableau": "Tableau",
}


@dataclass
class CleanedProfile:
    """Sanitised profile data ready for prompt assembly."""

    name: str
    email: str
    career_level: str
    education: list[dict[str, Any]]
    experience: list[dict[str, Any]]
    projects: list[dict[str, Any]]
    certifications: list[dict[str, Any]]
    skills: list[str]
    strengths: list[str]
    weblinks: dict[str, str]
    preferred_locations: list[str]
    preferred_sectors: list[str]
    warnings: list[str] = field(default_factory=list)


def _strip_html(text: str) -> str:
    """Remove HTML tags, keep text content."""
    return re.sub(r"<[^>]+>", "", text)


def _normalise_text(text: Optional[str]) -> str:
    """Strip, normalise unicode, remove control chars, strip HTML."""
    if not text:
        return ""
    # Normalise unicode
    text = unicodedata.normalize("NFKC", text)
    # Remove control characters (but keep newlines and tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Strip HTML tags
    text = _strip_html(text)
    return text.strip()


def _normalise_skill(skill: str) -> str:
    """Normalise a skill name to its canonical form."""
    cleaned = _normalise_text(skill)
    if not cleaned:
        return ""
    lookup = cleaned.lower().strip()
    return _SKILL_ALIASES.get(lookup, cleaned)


def _dedupe_strings(items: list[str]) -> list[str]:
    """Deduplicate strings case-insensitively, preserving first occurrence."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _clean_education(edu_list) -> tuple[list[dict[str, Any]], list[str]]:
    """Clean and deduplicate education entries."""
    warnings: list[str] = []
    cleaned: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for edu in edu_list or []:
        degree = _normalise_text(getattr(edu, "degree", None) or "")
        institute = _normalise_text(getattr(edu, "institute", None) or "")
        field_of_study = _normalise_text(getattr(edu, "field_of_study", None) or "")
        passing_year = getattr(edu, "passing_year", None)
        cgpa = _normalise_text(getattr(edu, "cgpa", None) or "")
        qual_level = _normalise_text(getattr(edu, "qualification_level", None) or "")

        # Dedup key
        key = f"{degree}|{institute}|{field_of_study}".lower()
        if key in seen_keys:
            warnings.append(
                f"Duplicate education entry removed: {degree} at {institute}"
            )
            continue
        seen_keys.add(key)

        # Skip completely empty
        if not degree and not institute and not field_of_study:
            continue

        entry: dict[str, Any] = {}
        if qual_level:
            entry["qualification_level"] = qual_level
        if degree:
            entry["degree"] = degree
        if institute:
            entry["institution"] = institute
        if field_of_study:
            entry["field_of_study"] = field_of_study
        if passing_year:
            entry["year"] = passing_year
        if cgpa:
            entry["cgpa"] = cgpa
        cleaned.append(entry)

    return cleaned, warnings


def _clean_experience(exp_list) -> tuple[list[dict[str, Any]], list[str]]:
    """Clean and deduplicate experience entries."""
    warnings: list[str] = []
    cleaned: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for exp in exp_list or []:
        company = _normalise_text(getattr(exp, "company_name", None) or "")
        role = _normalise_text(getattr(exp, "role", None) or "")
        designation = _normalise_text(getattr(exp, "designation", None) or "")
        emp_type = _normalise_text(getattr(exp, "employment_type", None) or "")
        responsibilities = _normalise_text(getattr(exp, "responsibilities", None) or "")
        from_date = getattr(exp, "from_date", None)
        to_date = getattr(exp, "to_date", None)
        is_current = getattr(exp, "is_current", False)

        title = role or designation or ""

        # Dedup key
        key = f"{title}|{company}".lower()
        if key in seen_keys and key != "|":
            warnings.append(f"Duplicate experience entry removed: {title} at {company}")
            continue
        seen_keys.add(key)

        # Skip completely empty
        if not title and not company and not responsibilities:
            continue

        entry: dict[str, Any] = {}
        if title:
            entry["title"] = title
        if company:
            entry["company"] = company
        if emp_type:
            entry["employment_type"] = emp_type
        if from_date:
            entry["from_date"] = str(from_date)
        if to_date:
            entry["to_date"] = str(to_date)
        elif is_current:
            entry["to_date"] = "Present"
        if responsibilities:
            entry["responsibilities"] = responsibilities
        cleaned.append(entry)

    return cleaned, warnings


def _clean_projects(proj_list) -> tuple[list[dict[str, Any]], list[str]]:
    """Clean and deduplicate project entries."""
    warnings: list[str] = []
    cleaned: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for proj in proj_list or []:
        name = _normalise_text(getattr(proj, "project_name", None) or "")
        org = _normalise_text(getattr(proj, "org", None) or "")
        tools = _normalise_text(getattr(proj, "tools_used", None) or "")
        responsibilities = _normalise_text(
            getattr(proj, "responsibilities", None) or ""
        )
        achievements = _normalise_text(getattr(proj, "achievements", None) or "")

        key = name.lower()
        if key and key in seen_keys:
            warnings.append(f"Duplicate project removed: {name}")
            continue
        if key:
            seen_keys.add(key)

        if not name and not responsibilities and not achievements:
            continue

        entry: dict[str, Any] = {}
        if name:
            entry["name"] = name
        if org:
            entry["organization"] = org
        if tools:
            entry["technologies"] = tools
        if responsibilities:
            entry["description"] = responsibilities
        if achievements:
            entry["achievements"] = achievements
        cleaned.append(entry)

    return cleaned, warnings


def _clean_certifications(cert_list) -> tuple[list[dict[str, Any]], list[str]]:
    """Clean and deduplicate certification entries."""
    warnings: list[str] = []
    cleaned: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for cert in cert_list or []:
        name = _normalise_text(getattr(cert, "name", None) or "")
        issuer = _normalise_text(getattr(cert, "issuing_org", None) or "")
        date = getattr(cert, "completion_date", None)

        key = name.lower()
        if key and key in seen_keys:
            warnings.append(f"Duplicate certification removed: {name}")
            continue
        if key:
            seen_keys.add(key)

        if not name:
            continue

        entry: dict[str, Any] = {"name": name}
        if issuer:
            entry["issuer"] = issuer
        if date:
            entry["date"] = str(date)
        cleaned.append(entry)

    return cleaned, warnings


def clean_profile(profile: CandidateProfile, user_email: str = "") -> CleanedProfile:
    """Normalise, deduplicate, and sanitise a candidate profile.

    Returns a ``CleanedProfile`` with a ``warnings`` list noting
    everything that was cleaned or stripped.
    """
    warnings: list[str] = []

    # Basic fields
    career_level = _normalise_text(profile.career_level)
    if not career_level:
        career_level = "Not specified"
        warnings.append("Career level missing — defaulted to 'Not specified'")

    # Skills
    raw_skills: list[str] = []
    for cs in profile.skills or []:
        skill_obj = getattr(cs, "skill", None)
        if skill_obj:
            name = getattr(skill_obj, "name", "")
            normalised = _normalise_skill(name)
            if normalised:
                raw_skills.append(normalised)
    skills = _dedupe_strings(raw_skills)
    if not skills:
        warnings.append(
            "No skills found — resume will rely on experience and education only"
        )

    # Education
    education, edu_warnings = _clean_education(profile.education)
    warnings.extend(edu_warnings)

    # Experience
    experience, exp_warnings = _clean_experience(profile.experience)
    warnings.extend(exp_warnings)

    # Projects
    projects, proj_warnings = _clean_projects(profile.projects)
    warnings.extend(proj_warnings)

    # Certifications
    certifications, cert_warnings = _clean_certifications(
        getattr(profile, "certifications", [])
    )
    warnings.extend(cert_warnings)

    # Strengths
    strengths = _dedupe_strings([_normalise_text(s) for s in (profile.strengths or [])])

    # Name + weblinks
    raw_links = profile.weblinks or {}
    weblinks = {
        k: _normalise_text(v) for k, v in raw_links.items() if _normalise_text(v)
    }
    name = _normalise_text(raw_links.get("display_name", ""))

    # Locations / sectors
    preferred_locations = _dedupe_strings(
        [_normalise_text(loc) for loc in (profile.preferred_locations or [])]
    )
    preferred_sectors = _dedupe_strings(
        [_normalise_text(sec) for sec in (profile.preferred_sectors or [])]
    )

    return CleanedProfile(
        name=name,
        email=user_email,
        career_level=career_level,
        education=education,
        experience=experience,
        projects=projects,
        certifications=certifications,
        skills=skills,
        strengths=strengths,
        weblinks=weblinks,
        preferred_locations=preferred_locations,
        preferred_sectors=preferred_sectors,
        warnings=warnings,
    )
