"""Vertical-specific prompt supplements for resume generation and ATS scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerticalPrompt:
    """Prompt supplements for a specific industry vertical."""

    key_skills: list[str]
    resume_tone: str
    ats_keywords: list[str]
    emphasis_rules: str
    de_emphasis_rules: str


VERTICALS: dict[str, VerticalPrompt] = {
    "electronics": VerticalPrompt(
        key_skills=[
            "Circuit Design",
            "Embedded Systems",
            "VLSI",
            "FPGA",
            "PCB Design",
            "Verilog",
            "VHDL",
            "MATLAB",
            "Signal Processing",
            "Microcontrollers",
            "IoT",
            "Analog Design",
            "Digital Design",
            "Oscilloscope",
            "Soldering",
        ],
        resume_tone=(
            "Technical and precise. Emphasise hands-on lab work, hardware projects, "
            "and quantitative results (e.g. clock speeds, power consumption, yield improvements). "
            "Use industry-standard terminology."
        ),
        ats_keywords=[
            "circuit design",
            "embedded systems",
            "PCB",
            "FPGA",
            "VLSI",
            "signal processing",
            "microcontroller",
            "firmware",
            "hardware",
            "testing",
            "debug",
            "schematic",
            "simulation",
            "prototype",
            "lab",
            "oscilloscope",
            "multimeter",
        ],
        emphasis_rules=(
            "Highlight: hardware projects, lab experience, core electronics coursework, "
            "EDA tools, circuit simulation, test and measurement. "
            "Reframe software skills as 'embedded programming' or 'firmware development' where applicable."
        ),
        de_emphasis_rules=(
            "De-emphasise: pure web development, marketing, sales, UI/UX design details. "
            "Keep only if they demonstrate cross-functional breadth."
        ),
    ),
    "software": VerticalPrompt(
        key_skills=[
            "Python",
            "JavaScript",
            "TypeScript",
            "Java",
            "C++",
            "React",
            "Node.js",
            "SQL",
            "Git",
            "AWS",
            "Docker",
            "Kubernetes",
            "REST APIs",
            "CI/CD",
            "Agile",
            "System Design",
            "Data Structures",
            "Algorithms",
        ],
        resume_tone=(
            "Clear and technically detailed. Lead with impact metrics (e.g. reduced load time by 40%, "
            "served 10K daily users). Show full-stack breadth or specialisation depth. "
            "Mention specific frameworks, languages, and tools by name."
        ),
        ats_keywords=[
            "software development",
            "programming",
            "full-stack",
            "backend",
            "frontend",
            "API",
            "database",
            "cloud",
            "DevOps",
            "CI/CD",
            "agile",
            "scrum",
            "version control",
            "testing",
            "debugging",
            "deployment",
        ],
        emphasis_rules=(
            "Highlight: programming projects, open-source contributions, technical achievements, "
            "frameworks and tools used, performance improvements, team collaboration. "
            "Reframe hardware experience as 'embedded software' or 'systems programming'."
        ),
        de_emphasis_rules=(
            "De-emphasise: pure hardware lab work, marketing campaigns, sales figures. "
            "Keep analytical and automation skills even if from non-tech roles."
        ),
    ),
    "marketing": VerticalPrompt(
        key_skills=[
            "Content Strategy",
            "SEO",
            "SEM",
            "Social Media Marketing",
            "Google Analytics",
            "Campaign Management",
            "Brand Strategy",
            "Copywriting",
            "Email Marketing",
            "Market Research",
            "A/B Testing",
            "CRM",
            "Growth Hacking",
        ],
        resume_tone=(
            "Results-driven and creative. Lead with measurable outcomes (e.g. grew engagement 3x, "
            "increased conversion by 25%). Demonstrate storytelling ability and audience understanding. "
            "Balance creative vision with data-driven decision making."
        ),
        ats_keywords=[
            "marketing strategy",
            "digital marketing",
            "content creation",
            "SEO",
            "social media",
            "campaign",
            "analytics",
            "brand",
            "engagement",
            "conversion",
            "growth",
            "audience",
            "ROI",
            "lead generation",
        ],
        emphasis_rules=(
            "Highlight: communication skills, campaigns, content creation, analytics, "
            "client-facing work, presentations, data analysis for marketing. "
            "Reframe technical skills as 'marketing automation' or 'data-driven marketing'."
        ),
        de_emphasis_rules=(
            "De-emphasise: deep programming details, circuit design, hardware projects. "
            "Keep data analysis and tool proficiency but reframe for marketing context."
        ),
    ),
    "design": VerticalPrompt(
        key_skills=[
            "UI/UX Design",
            "Figma",
            "Sketch",
            "Adobe XD",
            "User Research",
            "Wireframing",
            "Prototyping",
            "Design Systems",
            "Typography",
            "Information Architecture",
            "Usability Testing",
            "Visual Design",
        ],
        resume_tone=(
            "Creative yet structured. Demonstrate user-centred thinking and process. "
            "Reference specific design methodologies and tools. "
            "Include portfolio links prominently."
        ),
        ats_keywords=[
            "UI design",
            "UX design",
            "user experience",
            "user interface",
            "wireframe",
            "prototype",
            "figma",
            "design system",
            "usability",
            "user research",
            "visual design",
            "interaction design",
            "responsive design",
        ],
        emphasis_rules=(
            "Highlight: design projects, user research, prototyping work, design tools, "
            "portfolio work, design thinking process, collaboration with developers."
        ),
        de_emphasis_rules=(
            "De-emphasise: backend development, hardware projects, deep algorithmic work. "
            "Keep front-end skills as they complement design work."
        ),
    ),
    "sales": VerticalPrompt(
        key_skills=[
            "CRM",
            "Pipeline Management",
            "Negotiation",
            "Client Relations",
            "B2B Sales",
            "Lead Generation",
            "Revenue Growth",
            "Account Management",
            "Sales Forecasting",
            "Cold Calling",
            "Presentation Skills",
        ],
        resume_tone=(
            "Metrics-driven and achievement-focused. Lead every bullet with quantifiable results "
            "(e.g. closed $2M in new business, grew territory 150%, retained 95% of accounts). "
            "Show relationship-building and strategic thinking."
        ),
        ats_keywords=[
            "sales",
            "revenue",
            "client",
            "account management",
            "pipeline",
            "negotiation",
            "business development",
            "lead generation",
            "CRM",
            "quota",
            "territory",
            "relationship management",
            "closing",
        ],
        emphasis_rules=(
            "Highlight: client-facing experience, revenue impact, relationship building, "
            "negotiation wins, CRM usage, presentation and communication skills."
        ),
        de_emphasis_rules=(
            "De-emphasise: deep technical implementation, coding projects, hardware labs. "
            "Keep analytical skills and tech literacy as differentiators."
        ),
    ),
    "data": VerticalPrompt(
        key_skills=[
            "SQL",
            "Python",
            "R",
            "Statistics",
            "Machine Learning",
            "Data Visualisation",
            "Tableau",
            "Power BI",
            "Excel",
            "ETL",
            "Big Data",
            "A/B Testing",
            "Pandas",
            "NumPy",
            "Scikit-learn",
            "TensorFlow",
        ],
        resume_tone=(
            "Analytical and precise. Emphasise quantitative achievements and insight generation. "
            "Show the full data pipeline: collection → cleaning → analysis → insight → impact. "
            "Reference specific tools, techniques, and statistical methods."
        ),
        ats_keywords=[
            "data analysis",
            "SQL",
            "Python",
            "statistics",
            "machine learning",
            "data visualisation",
            "ETL",
            "analytics",
            "insight",
            "reporting",
            "dashboard",
            "data-driven",
            "modelling",
            "A/B testing",
        ],
        emphasis_rules=(
            "Highlight: data projects, analytical tools, statistical methods, insight generation, "
            "quantitative coursework, business impact of analysis."
        ),
        de_emphasis_rules=(
            "De-emphasise: pure UI design, marketing creative, hardware projects. "
            "Keep programming skills that support data work."
        ),
    ),
    "product": VerticalPrompt(
        key_skills=[
            "Product Strategy",
            "Roadmap Planning",
            "Agile/Scrum",
            "Stakeholder Management",
            "User Stories",
            "Market Analysis",
            "A/B Testing",
            "Data Analysis",
            "Cross-functional Leadership",
            "Requirements Gathering",
        ],
        resume_tone=(
            "Strategic and cross-functional. Balance technical literacy with business acumen. "
            "Show ownership of product outcomes and user impact. "
            "Demonstrate ability to translate between technical and business stakeholders."
        ),
        ats_keywords=[
            "product management",
            "roadmap",
            "stakeholder",
            "agile",
            "scrum",
            "user stories",
            "requirements",
            "prioritisation",
            "metrics",
            "cross-functional",
            "strategy",
            "market analysis",
        ],
        emphasis_rules=(
            "Highlight: leadership, cross-functional collaboration, data-driven decisions, "
            "product outcomes, user research, strategic thinking."
        ),
        de_emphasis_rules=(
            "De-emphasise: deep implementation details. Keep technical skills as 'technical literacy'."
        ),
    ),
    "general": VerticalPrompt(
        key_skills=[
            "Communication",
            "Problem Solving",
            "Leadership",
            "Teamwork",
            "Project Management",
            "Critical Thinking",
            "Adaptability",
        ],
        resume_tone=(
            "Professional and well-rounded. Emphasise transferable strengths, "
            "adaptability, and diverse experience. Show a breadth of capabilities."
        ),
        ats_keywords=[
            "communication",
            "leadership",
            "teamwork",
            "problem solving",
            "project management",
            "collaboration",
            "analytical",
        ],
        emphasis_rules=(
            "Highlight: strongest transferable skills from all domains, leadership roles, "
            "team projects, achievements with measurable impact."
        ),
        de_emphasis_rules=(
            "Keep all experience — reframe for the specific role if possible."
        ),
    ),
}


def classify_vertical(vertical: str) -> str:
    """Map a free-form vertical string to a known bucket key."""
    v = vertical.lower()
    if any(
        k in v
        for k in ("electron", "ece", "hardware", "embedded", "circuit", "vlsi", "fpga")
    ):
        return "electronics"
    if any(k in v for k in ("market", "content", "seo", "brand", "growth")):
        return "marketing"
    if any(k in v for k in ("design", "ui", "ux", "figma")):
        return "design"
    if any(k in v for k in ("sales", "account exec", "business develop")):
        return "sales"
    if any(k in v for k in ("data", "analyst", "ml", "ai scientist")):
        return "data"
    if any(k in v for k in ("product",)):
        return "product"
    if any(
        k in v
        for k in (
            "software",
            "it",
            "developer",
            "engineer",
            "frontend",
            "backend",
            "devops",
            "fullstack",
        )
    ):
        return "software"
    return "general"


def get_vertical_prompt(vertical: str) -> VerticalPrompt:
    """Get the prompt supplement for a vertical (falls back to 'general')."""
    bucket = classify_vertical(vertical)
    return VERTICALS.get(bucket, VERTICALS["general"])
