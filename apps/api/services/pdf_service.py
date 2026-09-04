"""Server-side PDF generation from structured resume content using fpdf2."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from fpdf import FPDF

logger = logging.getLogger(__name__)


def _extract_contact(content: dict[str, Any], weblinks: Optional[dict] = None) -> dict[str, str]:
    info: dict[str, str] = {}
    weblinks = weblinks or content.get("weblinks", {}) or {}
    for key in ("linkedin", "LinkedIn", "LINKEDIN"):
        if weblinks.get(key):
            info["linkedin"] = str(weblinks[key])
            break
    for key in ("github", "GitHub", "GITHUB"):
        if weblinks.get(key):
            info["github"] = str(weblinks[key])
            break
    for key in ("portfolio", "Portfolio", "website", "Website"):
        if weblinks.get(key):
            info["portfolio"] = str(weblinks[key])
            break
    return info


def _normalise_skills(skills_data) -> dict[str, list[str]]:
    if isinstance(skills_data, dict):
        return {
            "technical": [str(s) for s in (skills_data.get("technical") or [])],
            "soft": [str(s) for s in (skills_data.get("soft") or [])],
        }
    if isinstance(skills_data, list):
        return {"technical": [str(s) for s in skills_data], "soft": []}
    return {"technical": [], "soft": []}


def _safe(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u00a0": " ",
        "\u2026": "...",
    }
    for src, dst in replacements.items():
        s = s.replace(src, dst)
    s = re.sub(r"[^\x09\x0a\x0d\x20-\x7e]", "", s)
    return s.strip()


class _ResumePDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _heading(pdf: FPDF, title: str) -> None:
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 6, _safe(title).upper(), ln=1)
    x1 = pdf.l_margin
    x2 = pdf.w - pdf.r_margin
    y = pdf.get_y()
    pdf.set_draw_color(160, 160, 160)
    pdf.line(x1, y, x2, y)
    pdf.ln(2)


def generate_pdf(
    resume_content: dict[str, Any],
    candidate_name: str = "Candidate",
    email: str = "",
    phone: str = "",
    location: str = "",
    weblinks: Optional[dict] = None,
) -> bytes:
    """Always return real PDF bytes (%PDF...). Uses fpdf2 (Windows-safe)."""
    contact = _extract_contact(resume_content, weblinks)
    skills = _normalise_skills(resume_content.get("skills", {}))
    summary = resume_content.get("professional_summary") or resume_content.get("summary") or ""

    pdf = _ResumePDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)
    usable = pdf.epw

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(usable, 8, _safe(candidate_name).upper() or "CANDIDATE", align="C")

    bits = [x for x in [_safe(location), _safe(email), _safe(phone)] if x]
    for key in ("linkedin", "github", "portfolio"):
        val = _safe(contact.get(key))
        if val:
            bits.append(val)
    if bits:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(usable, 5, " | ".join(bits), align="C")

    pdf.set_draw_color(20, 20, 20)
    y = pdf.get_y() + 1
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.set_y(y + 3)

    if summary:
        _heading(pdf, "Professional Summary")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(usable, 5, _safe(summary))

    experience = resume_content.get("experience") or []
    if experience:
        _heading(pdf, "Experience")
        for exp in experience:
            title = _safe(exp.get("title"))
            company = _safe(exp.get("company"))
            dates = _safe(exp.get("dates"))
            left = " - ".join(p for p in [title, company] if p)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(20, 20, 20)
            if left:
                pdf.multi_cell(usable, 5, left)
            if dates:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(90, 90, 90)
                pdf.multi_cell(usable, 4, dates)
            bullets = exp.get("bullets") or []
            if isinstance(bullets, str):
                bullets = [bullets]
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(40, 40, 40)
            for b in bullets:
                text = _safe(b)
                if text:
                    pdf.multi_cell(usable, 4.5, f"- {text}")
            pdf.ln(1)

    education = resume_content.get("education") or []
    if education:
        _heading(pdf, "Education")
        for edu in education:
            degree = _safe(edu.get("degree"))
            institution = _safe(edu.get("institution"))
            year = _safe(edu.get("year"))
            line = " - ".join(p for p in [degree, institution] if p)
            if year:
                line = f"{line} ({year})" if line else year
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(20, 20, 20)
            if line:
                pdf.multi_cell(usable, 5, line)
            highlights = edu.get("highlights") or []
            if isinstance(highlights, str):
                highlights = [highlights]
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(40, 40, 40)
            for h in highlights:
                text = _safe(h)
                if text:
                    pdf.multi_cell(usable, 4.5, f"- {text}")
            pdf.ln(1)

    tech = skills.get("technical") or []
    soft = skills.get("soft") or []
    if tech or soft:
        _heading(pdf, "Skills")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        if tech:
            pdf.multi_cell(usable, 5, _safe("Technical: " + ", ".join(tech)))
        if soft:
            pdf.multi_cell(usable, 5, _safe("Soft: " + ", ".join(soft)))

    projects = resume_content.get("projects") or []
    if projects:
        _heading(pdf, "Projects")
        for proj in projects:
            name = _safe(proj.get("name") or "Project")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(20, 20, 20)
            pdf.multi_cell(usable, 5, name)
            desc = _safe(proj.get("description"))
            if desc:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(40, 40, 40)
                pdf.multi_cell(usable, 4.5, desc)
            techs = proj.get("technologies") or []
            if isinstance(techs, str):
                techs = [t.strip() for t in techs.split(",") if t.strip()]
            if techs:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(90, 90, 90)
                pdf.multi_cell(usable, 4, _safe("Tech: " + ", ".join(str(t) for t in techs)))
            pdf.ln(1)

    certifications = resume_content.get("certifications") or []
    if certifications:
        _heading(pdf, "Certifications")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        for cert in certifications:
            if isinstance(cert, dict):
                name = cert.get("name") or cert.get("title") or ""
                org = cert.get("issuer") or cert.get("issuing_org") or ""
                line = _safe(f"{name}" + (f" - {org}" if org else ""))
            else:
                line = _safe(cert)
            if line:
                pdf.multi_cell(usable, 5, f"- {line}")

    out = pdf.output()
    data = bytes(out) if not isinstance(out, (bytes, bytearray)) else bytes(out)
    if data[:4] != b"%PDF":
        raise RuntimeError("fpdf2 did not produce a valid PDF")
    return data


def create_pdf_response(pdf_bytes: bytes, filename: str) -> Any:
    from fastapi import HTTPException, Response

    if pdf_bytes[:4] != b"%PDF":
        raise HTTPException(status_code=500, detail="Generated file is not a valid PDF")
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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

        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc
    return create_pdf_response(pdf_bytes, filename)
