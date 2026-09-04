"""Server-side PDF generation from structured resume content using fpdf2."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from fpdf import FPDF

logger = logging.getLogger(__name__)


def display_name_from_email(email: str) -> str:
    return email.split("@")[0].replace(".", " ").title() if email else "Candidate"


def resolve_candidate_name(
    *,
    candidate_name: Optional[str] = None,
    weblinks: Optional[dict] = None,
    email: str = "",
) -> str:
    """Prefer explicit name / weblinks.display_name over email local-part."""
    if candidate_name and str(candidate_name).strip():
        return str(candidate_name).strip()
    links = weblinks or {}
    for key in ("display_name", "full_name", "name"):
        val = links.get(key)
        if val and str(val).strip():
            return str(val).strip()
    return display_name_from_email(email)


def _ensure_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not re.match(r"^https?://", u, re.I):
        return f"https://{u}"
    return u


def _extract_contact(
    content: dict[str, Any], weblinks: Optional[dict] = None
) -> dict[str, str]:
    info: dict[str, str] = {}
    merged: dict[str, Any] = {}
    if isinstance(content.get("weblinks"), dict):
        merged.update(content["weblinks"])
    if weblinks:
        merged.update(weblinks)

    for key in ("linkedin", "LinkedIn", "LINKEDIN"):
        if merged.get(key):
            info["linkedin"] = _ensure_url(str(merged[key]))
            break
    for key in ("github", "GitHub", "GITHUB"):
        if merged.get(key):
            info["github"] = _ensure_url(str(merged[key]))
            break
    for key in ("portfolio", "Portfolio", "website", "Website"):
        if merged.get(key):
            info["portfolio"] = _ensure_url(str(merged[key]))
            break
    for key in ("phone", "Phone", "mobile", "Mobile"):
        if merged.get(key):
            info["phone"] = str(merged[key]).strip()
            break
    return info


def _normalise_skills(skills_data) -> dict[str, list[str]]:
    if isinstance(skills_data, dict):
        # Support category maps like Languages / Frameworks from richer content
        known = {"technical", "soft"}
        out: dict[str, list[str]] = {"technical": [], "soft": []}
        for k, v in skills_data.items():
            items = (
                [str(s).strip() for s in (v or []) if str(s).strip()]
                if isinstance(v, list)
                else []
            )
            if not items:
                continue
            key = str(k).lower()
            if key in known:
                out[key] = items
            else:
                out[str(k)] = items
        return out
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


def _project_url(proj: dict) -> str:
    for key in ("url", "link", "href", "project_url", "github", "demo"):
        val = proj.get(key)
        if val:
            return _ensure_url(str(val))
    return ""


class _ResumePDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _heading(pdf: FPDF, title: str) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(26, 26, 26)
    pdf.cell(0, 5, _safe(title).upper(), ln=1)
    x1 = pdf.l_margin
    x2 = pdf.w - pdf.r_margin
    y = pdf.get_y()
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)
    pdf.line(x1, y, x2, y)
    pdf.ln(2.5)


def _row_left_right(
    pdf: FPDF, left: str, right: str, *, left_style: str = "B", size: float = 10
) -> None:
    """Print left-aligned title and right-aligned date on one line."""
    usable = pdf.epw
    right_txt = _safe(right)
    left_txt = _safe(left)
    pdf.set_font("Helvetica", "I", size - 1)
    right_w = pdf.get_string_width(right_txt) + 2 if right_txt else 0
    left_w = usable - right_w

    pdf.set_font("Helvetica", left_style, size)
    pdf.set_text_color(26, 26, 26)
    pdf.cell(left_w, 5, (left_txt or " ")[:120], ln=0)
    if right_txt:
        pdf.set_font("Helvetica", "I", size - 1)
        pdf.set_text_color(85, 85, 85)
        pdf.cell(right_w, 5, right_txt, align="R", ln=1)
    else:
        pdf.ln(5)


def _link_label(pdf: FPDF, label: str, url: str) -> None:
    """Inline clickable link in accent blue."""
    url = _ensure_url(url)
    if not url:
        return
    pdf.set_font("Helvetica", "U", 9)
    pdf.set_text_color(37, 99, 235)
    pdf.write(4.5, _safe(label), link=url)
    pdf.set_text_color(40, 40, 40)


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
    phone = phone or contact.get("phone") or ""
    skills = _normalise_skills(resume_content.get("skills", {}))
    summary = (
        resume_content.get("professional_summary")
        or resume_content.get("summary")
        or ""
    )
    location = location or _safe(resume_content.get("location") or "")

    pdf = _ResumePDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)
    usable = pdf.epw

    # ── Header name ──────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 26, 26)
    name = _safe(candidate_name) or "Candidate"
    pdf.multi_cell(usable, 8, name, align="C")

    # ── Contact line with clickable links ────────────────────────────────
    contact_parts: list[tuple[str, Optional[str]]] = []
    if email:
        contact_parts.append((_safe(email), f"mailto:{email}"))
    if phone:
        contact_parts.append((_safe(phone), f"tel:{re.sub(r'[^0-9+]', '', phone)}"))
    if location:
        contact_parts.append((_safe(location), None))
    for key, label in (
        ("linkedin", "LinkedIn"),
        ("github", "GitHub"),
        ("portfolio", "Portfolio"),
    ):
        url = contact.get(key)
        if url:
            contact_parts.append((label, url))

    if contact_parts:
        pdf.ln(1)
        # Center by measuring total width
        pdf.set_font("Helvetica", "", 9)
        sep = "  |  "
        widths = []
        for text, link in contact_parts:
            if link and text in ("LinkedIn", "GitHub", "Portfolio"):
                pdf.set_font("Helvetica", "U", 9)
            else:
                pdf.set_font("Helvetica", "", 9)
            widths.append(pdf.get_string_width(text))
        sep_w = pdf.get_string_width(sep)
        total = sum(widths) + sep_w * max(0, len(contact_parts) - 1)
        x = pdf.l_margin + max(0, (usable - total) / 2)
        y = pdf.get_y()
        pdf.set_xy(x, y)
        for i, (text, link) in enumerate(contact_parts):
            if link and text in ("LinkedIn", "GitHub", "Portfolio"):
                pdf.set_font("Helvetica", "U", 9)
                pdf.set_text_color(37, 99, 235)
                pdf.cell(widths[i], 5, text, link=link)
            elif link and text == _safe(email):
                pdf.set_font("Helvetica", "U", 9)
                pdf.set_text_color(70, 70, 70)
                pdf.cell(widths[i], 5, text, link=link)
            else:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(70, 70, 70)
                pdf.cell(widths[i], 5, text)
            if i < len(contact_parts) - 1:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(150, 150, 150)
                pdf.cell(sep_w, 5, sep)
        pdf.ln(6)

    pdf.set_draw_color(26, 26, 26)
    pdf.set_line_width(0.5)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.set_y(y + 3)

    # ── Summary ──────────────────────────────────────────────────────────
    if summary:
        _heading(pdf, "Professional Summary")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(42, 42, 42)
        pdf.multi_cell(usable, 5, _safe(summary))

    # ── Experience ───────────────────────────────────────────────────────
    experience = resume_content.get("experience") or []
    if experience:
        _heading(pdf, "Experience")
        for exp in experience:
            title = _safe(exp.get("title"))
            company = _safe(exp.get("company"))
            dates = _safe(exp.get("dates"))
            location_exp = _safe(
                exp.get("location") or exp.get("employment_type") or ""
            )
            _row_left_right(pdf, title or "Role", dates)
            if company or location_exp:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(51, 51, 51)
                _row_left_right(pdf, company, location_exp, left_style="I", size=9)
            bullets = exp.get("bullets") or []
            if isinstance(bullets, str):
                bullets = [bullets]
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(40, 40, 40)
            for b in bullets:
                text = _safe(b)
                if text:
                    pdf.multi_cell(usable, 4.5, f"- {text}")
            pdf.ln(1.5)

    # ── Education ────────────────────────────────────────────────────────
    education = resume_content.get("education") or []
    if education:
        _heading(pdf, "Education")
        for edu in education:
            degree = _safe(edu.get("degree"))
            institution = _safe(edu.get("institution"))
            year = _safe(edu.get("year"))
            gpa = _safe(edu.get("gpa") or edu.get("cgpa") or "")
            left = institution or degree
            _row_left_right(pdf, left, year)
            if institution and degree:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(51, 51, 51)
                pdf.multi_cell(usable, 4.5, degree)
            if gpa:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(70, 70, 70)
                pdf.multi_cell(
                    usable, 4.5, f"CGPA: {gpa}" if "cgpa" not in gpa.lower() else gpa
                )
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

    # ── Skills ───────────────────────────────────────────────────────────
    skill_cats = [(k, v) for k, v in skills.items() if v]
    if skill_cats:
        _heading(pdf, "Skills")
        for cat, items in skill_cats:
            label = (
                "Technical"
                if cat == "technical"
                else ("Soft" if cat == "soft" else str(cat).title())
            )
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(26, 26, 26)
            pdf.write(5, f"{label}: ")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(40, 40, 40)
            pdf.write(5, _safe(", ".join(items)))
            pdf.ln(5)

    # ── Projects ─────────────────────────────────────────────────────────
    projects = resume_content.get("projects") or []
    if projects:
        _heading(pdf, "Projects")
        for proj in projects:
            name_p = _safe(proj.get("name") or "Project")
            url = _project_url(proj)
            subtitle = _safe(proj.get("subtitle") or proj.get("tagline") or "")
            y = pdf.get_y()
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(26, 26, 26)
            pdf.write(5, name_p)
            if url:
                pdf.write(5, "  ")
                _link_label(pdf, "Link", url)
            if subtitle:
                # push subtitle toward the right on same visual row when short
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(85, 85, 85)
                pdf.write(5, f"  —  {subtitle}")
            pdf.ln(5)
            techs = proj.get("technologies") or []
            if isinstance(techs, str):
                techs = [t.strip() for t in techs.split(",") if t.strip()]
            if techs:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(90, 90, 90)
                pdf.multi_cell(usable, 4, _safe(", ".join(str(t) for t in techs)))
            desc = _safe(proj.get("description"))
            bullets = proj.get("bullets") or []
            if isinstance(bullets, str):
                bullets = [bullets]
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(40, 40, 40)
            if desc and not bullets:
                pdf.multi_cell(usable, 4.5, f"- {desc}")
            for b in bullets:
                text = _safe(b)
                if text:
                    pdf.multi_cell(usable, 4.5, f"- {text}")
            if not bullets and not desc and y:
                pass
            pdf.ln(1.5)

    # ── Certifications / Achievements ────────────────────────────────────
    certifications = resume_content.get("certifications") or []
    if certifications:
        _heading(pdf, "Certifications")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        for cert in certifications:
            if isinstance(cert, dict):
                cname = cert.get("name") or cert.get("title") or ""
                org = cert.get("issuer") or cert.get("issuing_org") or ""
                line = _safe(f"{cname}" + (f" — {org}" if org else ""))
            else:
                line = _safe(cert)
            if line:
                pdf.multi_cell(usable, 5, f"- {line}")

    achievements = resume_content.get("achievements") or []
    if achievements:
        _heading(pdf, "Achievements")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        for a in achievements:
            text = _safe(
                a if not isinstance(a, dict) else a.get("title") or a.get("name") or ""
            )
            if text:
                pdf.multi_cell(usable, 5, f"- {text}")

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


def build_resume_pdf_response(
    *,
    resume_content: dict[str, Any],
    email: str,
    weblinks: Optional[dict] = None,
    filename: str,
    candidate_name: Optional[str] = None,
    phone: str = "",
    location: str = "",
) -> Any:
    name = resolve_candidate_name(
        candidate_name=candidate_name,
        weblinks=weblinks,
        email=email,
    )
    try:
        pdf_bytes = generate_pdf(
            resume_content=resume_content,
            candidate_name=name,
            email=email,
            phone=phone,
            location=location,
            weblinks=weblinks or {},
        )
    except Exception as exc:
        from fastapi import HTTPException

        logger.exception("PDF generation failed")
        raise HTTPException(
            status_code=500, detail=f"PDF generation failed: {exc}"
        ) from exc
    return create_pdf_response(pdf_bytes, filename)
