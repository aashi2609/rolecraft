"""Parse job-description PDFs/text into structured fields for job create autofill."""
from __future__ import annotations

import io
import logging
import re
from typing import Any

from fastapi import HTTPException

from core.config import get_settings
from services.ai_client import AIServiceError, generate_content

logger = logging.getLogger(__name__)
settings = get_settings()

_PARSE_SYSTEM = "You are a strict JSON-returning AI. Return only a JSON object, no markdown."

_PARSE_PROMPT = """\
You are an expert job-description parser. Extract hiring fields from the JD text below.

Return JSON with this exact schema (omit unknown fields or use null):
{{
  "title": "Job title",
  "job_role": "Role family e.g. Software Engineering, Product, Data",
  "job_level": "One of: Internship, Entry, Mid, Senior, Director, Executive",
  "experience_min": 0,
  "experience_max": 5,
  "experience_range": "2-5 years",
  "min_salary": 800000,
  "max_salary": 1500000,
  "salary_unit": "Per annum",
  "country": "India",
  "state": "Karnataka",
  "city": "Bengaluru",
  "location": "Bengaluru, Karnataka, India",
  "employment_type": "Full-time",
  "job_type": "hybrid",
  "department": "Engineering",
  "description": "About the role paragraph(s)",
  "responsibilities": "Bullet list as newline-separated text",
  "requirements": "Bullet list as newline-separated text",
  "benefits": "Bullet list as newline-separated text",
  "required_skills": ["Python", "React", "SQL"]
}}

Rules:
- Salaries: if LPA/INR lakhs, convert to annual INR integers (e.g. 12 LPA -> 1200000).
- job_type must be one of: onsite, remote, hybrid (lowercase).
- experience_min / experience_max are integers (years).
- Prefer Indian location fields when the JD is India-based.

JD TEXT:
{text}
"""


def extract_text_from_upload(file_data: bytes, filename: str = "") -> str:
    """Extract plain text from PDF or UTF-8 text bytes."""
    name = (filename or "").lower()
    if file_data.startswith(b"%PDF") or name.endswith(".pdf"):
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(file_data))
            parts: list[str] = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            text = "\n".join(parts).strip()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to read PDF: {exc}") from exc
        if not text:
            raise HTTPException(status_code=400, detail="No extractable text found in PDF")
        return text

    try:
        return file_data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return file_data.decode("latin-1")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Unsupported file encoding: {exc}") from exc


def _heuristic_parse(text: str) -> dict[str, Any]:
    """Deterministic fallback when Groq is unavailable."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lower = text.lower()

    def field(prefixes: list[str]) -> str | None:
        for line in lines:
            for p in prefixes:
                if line.lower().startswith(p.lower()):
                    return line[len(p) :].lstrip(" :-").strip() or None
        return None

    title = field(["Job Title", "Title", "Position"])
    role = field(["Role", "Job Role", "Function"])
    level = field(["Level", "Job Level", "Seniority"])
    emp = field(["Employment Type", "Employment"])
    department = field(["Department", "Team"])
    loc = field(["Location"])
    exp = field(["Experience", "Exp", "Years of Experience"])
    salary = field(["Salary", "Compensation", "CTC"])

    city = state = country = None
    if loc:
        parts = [p.strip() for p in loc.split(",") if p.strip()]
        if len(parts) >= 3:
            city, state, country = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            city, country = parts[0], parts[1]
        elif len(parts) == 1:
            city = parts[0]

    exp_min = exp_max = None
    exp_range = exp
    if exp:
        nums = [int(n) for n in re.findall(r"\d+", exp)]
        if len(nums) >= 2:
            exp_min, exp_max = nums[0], nums[1]
            exp_range = f"{exp_min}-{exp_max} years"
        elif len(nums) == 1:
            exp_min = nums[0]
            exp_max = nums[0] + 2
            exp_range = f"{exp_min}-{exp_max} years"

    min_salary = max_salary = None
    if salary:
        # 12-18 LPA or 1200000-1800000
        lpa = re.findall(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*lpa", salary, re.I)
        if lpa:
            a, b = float(lpa[0][0]), float(lpa[0][1])
            min_salary, max_salary = int(a * 100000), int(b * 100000)
        else:
            nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]+", salary)]
            if len(nums) >= 2:
                min_salary, max_salary = nums[0], nums[1]
            elif len(nums) == 1:
                min_salary = max_salary = nums[0]

    def section_after(headers: list[str]) -> str:
        for i, line in enumerate(lines):
            for h in headers:
                if line.lower().startswith(h.lower()):
                    buf: list[str] = []
                    for nxt in lines[i + 1 :]:
                        if re.match(
                            r"^(about|responsibilit|requirement|qualificat|benefit|skill|job title|location|experience|salary)",
                            nxt,
                            re.I,
                        ):
                            break
                        buf.append(nxt)
                    return "\n".join(buf).strip()
        return ""

    description = section_after(["About the Role", "About the Job", "Job Description", "Overview"])
    responsibilities = section_after(["Responsibilities", "What you'll do", "Key Responsibilities"])
    requirements = section_after(["Requirements", "Qualifications", "What we're looking for"])
    benefits = section_after(["Benefits", "Perks", "What we offer"])

    skills: list[str] = []
    skill_line = field(["Skills", "Required Skills", "Tech Stack"])
    if skill_line:
        skills = [s.strip() for s in re.split(r"[,|/]", skill_line) if s.strip()]
    common = [
        "Python", "Java", "JavaScript", "TypeScript", "React", "Next.js", "Node.js",
        "FastAPI", "Django", "SQL", "PostgreSQL", "AWS", "Docker", "Kubernetes",
    ]
    for s in common:
        if s.lower() in lower and s not in skills:
            skills.append(s)

    job_type = None
    if "remote" in lower:
        job_type = "remote"
    elif "hybrid" in lower:
        job_type = "hybrid"
    elif "on-site" in lower or "onsite" in lower:
        job_type = "onsite"

    level_norm = None
    if level:
        for opt in ("Internship", "Entry", "Mid", "Senior", "Director", "Executive"):
            if opt.lower() in level.lower():
                level_norm = opt
                break

    return {
        "title": title,
        "job_role": role,
        "job_level": level_norm or level,
        "experience_min": exp_min,
        "experience_max": exp_max,
        "experience_range": exp_range,
        "min_salary": min_salary,
        "max_salary": max_salary,
        "salary_unit": "Per annum",
        "country": country,
        "state": state,
        "city": city,
        "location": loc,
        "employment_type": emp,
        "job_type": job_type,
        "department": department,
        "description": description or None,
        "responsibilities": responsibilities or None,
        "requirements": requirements or None,
        "benefits": benefits or None,
        "required_skills": skills[:20],
        "parse_source": "heuristic",
    }


def _normalize_parsed(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    # experience_range from min/max if missing
    emin = out.get("experience_min")
    emax = out.get("experience_max")
    if not out.get("experience_range") and emin is not None and emax is not None:
        out["experience_range"] = f"{emin}-{emax} years"
    # location from parts
    if not out.get("location"):
        parts = [out.get("city"), out.get("state"), out.get("country")]
        loc = ", ".join(p for p in parts if p)
        if loc:
            out["location"] = loc
    # job_type normalize
    jt = (out.get("job_type") or "").lower().replace("-", "").replace(" ", "")
    if jt in ("onsite", "remote", "hybrid"):
        out["job_type"] = jt
    elif jt:
        out["job_type"] = "hybrid"
    # skills list
    skills = out.get("required_skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    out["required_skills"] = [str(s) for s in skills][:30]
    if "parse_source" not in out:
        out["parse_source"] = "llm"
    return out


async def parse_job_description(
    file_data: bytes,
    filename: str = "",
) -> dict[str, Any]:
    text = extract_text_from_upload(file_data, filename)
    text = text[:15000]

    if not settings.groq_api_key:
        logger.info("JD parse using heuristic fallback (no GROQ_API_KEY)")
        return _normalize_parsed(_heuristic_parse(text))

    prompt = _PARSE_PROMPT.format(text=text)
    try:
        parsed = await generate_content(
            prompt=prompt,
            system_instruction=_PARSE_SYSTEM,
            response_mime_type="application/json",
            temperature=0.2,
        )
        if not isinstance(parsed, dict):
            raise AIServiceError("JD parse response was not an object")
        return _normalize_parsed(parsed)
    except AIServiceError as exc:
        logger.warning("JD LLM parse failed, heuristic fallback: %s", exc)
        result = _normalize_parsed(_heuristic_parse(text))
        result["parse_source"] = "heuristic_fallback"
        result["parse_warning"] = str(exc)
        return result
