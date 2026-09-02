"""Server-side PDF generation from structured resume content.

Uses WeasyPrint (primary) for high-quality HTML→PDF rendering.
Falls back to a basic HTML file if WeasyPrint is not installed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=True,
)


def _extract_contact(content: dict[str, Any], weblinks: Optional[dict] = None) -> dict[str, str]:
    """Pull contact fields from resume content + weblinks."""
    info: dict[str, str] = {}
    weblinks = weblinks or content.get("weblinks", {}) or {}
    for key in ("linkedin", "LinkedIn", "LINKEDIN"):
        if weblinks.get(key):
            info["linkedin"] = weblinks[key]
            break
    for key in ("github", "GitHub", "GITHUB"):
        if weblinks.get(key):
            info["github"] = weblinks[key]
            break
    for key in ("portfolio", "Portfolio", "website", "Website"):
        if weblinks.get(key):
            info["portfolio"] = weblinks[key]
            break
    return info


def _normalise_skills(skills_data) -> dict[str, list[str]]:
    """Ensure skills is always {technical: [...], soft: [...]}."""
    if isinstance(skills_data, dict):
        return {
            "technical": skills_data.get("technical", []),
            "soft": skills_data.get("soft", []),
        }
    if isinstance(skills_data, list):
        return {"technical": skills_data, "soft": []}
    return {"technical": [], "soft": []}


def render_resume_html(
    resume_content: dict[str, Any],
    candidate_name: str = "Candidate",
    email: str = "",
    phone: str = "",
    location: str = "",
    weblinks: Optional[dict] = None,
) -> str:
    """Render the resume content into an HTML string using the LaTeX-style template."""
    template = _jinja_env.get_template("resume_template.html")

    contact = _extract_contact(resume_content, weblinks)
    skills = _normalise_skills(resume_content.get("skills", {}))

    # Clean up experience bullets — ensure they are lists of strings
    experience = []
    for exp in resume_content.get("experience", []):
        bullets = exp.get("bullets", [])
        if isinstance(bullets, str):
            bullets = [bullets]
        experience.append({
            "title": exp.get("title", ""),
            "company": exp.get("company", ""),
            "dates": exp.get("dates", ""),
            "bullets": bullets,
        })

    # Clean up education highlights
    education = []
    for edu in resume_content.get("education", []):
        highlights = edu.get("highlights", [])
        if isinstance(highlights, str):
            highlights = [highlights]
        education.append({
            "degree": edu.get("degree", ""),
            "institution": edu.get("institution", ""),
            "year": str(edu.get("year", "")),
            "highlights": [h for h in highlights if h],
        })

    # Clean up projects
    projects = []
    for proj in resume_content.get("projects", []):
        techs = proj.get("technologies", [])
        if isinstance(techs, str):
            techs = [t.strip() for t in techs.split(",")]
        projects.append({
            "name": proj.get("name", ""),
            "description": proj.get("description", ""),
            "technologies": techs,
        })

    # Certifications
    certifications = resume_content.get("certifications", [])

    html = template.render(
        name=candidate_name,
        email=email,
        phone=phone,
        location=location,
        linkedin=contact.get("linkedin", ""),
        github=contact.get("github", ""),
        portfolio=contact.get("portfolio", ""),
        professional_summary=resume_content.get(
            "professional_summary",
            resume_content.get("summary", ""),
        ),
        experience=experience,
        education=education,
        skills=skills,
        projects=projects,
        certifications=certifications,
    )
    return html


def generate_pdf(
    resume_content: dict[str, Any],
    candidate_name: str = "Candidate",
    email: str = "",
    phone: str = "",
    location: str = "",
    weblinks: Optional[dict] = None,
) -> bytes:
    """Generate a PDF from the resume content.

    Returns raw PDF bytes. Uses WeasyPrint if available, otherwise
    raises an ImportError with a helpful message.
    """
    html = render_resume_html(
        resume_content,
        candidate_name=candidate_name,
        email=email,
        phone=phone,
        location=location,
        weblinks=weblinks,
    )

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes
    except ImportError:
        logger.warning(
            "WeasyPrint is not installed. Install it with: pip install weasyprint. "
            "Returning raw HTML as fallback."
        )
        # Return HTML as PDF-like bytes (browser can open it)
        return html.encode("utf-8")


def create_pdf_response(
    pdf_bytes: bytes,
    filename: str,
) -> Any:
    """Create a FastAPI Response object for PDF download."""
    from fastapi import Response

    is_pdf = pdf_bytes[:4] == b"%PDF"
    media_type = "application/pdf" if is_pdf else "text/html"

    return Response(
        content=pdf_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def display_name_from_email(email: str) -> str:
    return email.split("@")[0].replace(".", " ").title() if email else "Candidate"


def build_resume_pdf_response(
    *,
    resume_content: dict[str, Any],
    email: str,
    weblinks: Optional[dict] = None,
    filename: str,
    candidate_name: Optional[str] = None,
) -> Any:
    """Generate PDF bytes and wrap as a download Response."""
    name = candidate_name or display_name_from_email(email)
    try:
        pdf_bytes = generate_pdf(
            resume_content=resume_content,
            candidate_name=name,
            email=email,
            weblinks=weblinks or {},
        )
    except Exception as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc

    return create_pdf_response(pdf_bytes, filename)
