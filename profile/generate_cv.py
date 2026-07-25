"""
Genera CV en formato Harvard para Mickaell Moran.
Uso: .venv/bin/python3 profile/generate_cv.py
Produce: profile/cv_es.docx  y  profile/cv_en.docx
PDF: libreoffice --headless --convert-to pdf --outdir profile profile/cv_es.docx profile/cv_en.docx
"""

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

TEXT_WIDTH_INCHES = 7.66  # 8.5" page - 0.42" * 2 margins


# ── helpers ────────────────────────────────────────────────────────────────────

def _add_right_tab(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:pos"), str(int(TEXT_WIDTH_INCHES * 1440)))
    tabs.append(tab)
    pPr.append(tabs)


def _add_bottom_border(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "000000")
    pBdr.append(bottom)
    pPr.append(pBdr)


def _set_spacing(paragraph, before=0, after=0):
    pf = paragraph.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = Pt(12)


def _set_margins(doc):
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.42)
        section.right_margin = Inches(0.42)


def _base_run(paragraph, text, bold=False, italic=False, size=11):
    run = paragraph.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    return run


# ── building blocks ─────────────────────────────────────────────────────────────

def add_name(doc, name):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_spacing(p, before=0, after=2)
    _base_run(p, name, bold=True, size=16)


def add_contact(doc, line1, line2=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_spacing(p, before=0, after=6)
    _base_run(p, line1, size=9.5)
    if line2:
        p.add_run("\n")
        _base_run(p, line2, size=9.5)


def add_section(doc, title):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_bottom_border(p)
    _set_spacing(p, before=8, after=2)
    _base_run(p, title.upper(), bold=True, size=11)


def add_org_line(doc, org, location, space_before=4):
    """Bold org name [TAB] location (right-aligned)."""
    p = doc.add_paragraph()
    _add_right_tab(p)
    _set_spacing(p, before=space_before, after=0)
    _base_run(p, org, bold=True)
    _base_run(p, "\t")
    _base_run(p, location)


def add_role_line(doc, role, date):
    """Italic role [TAB] date (right-aligned)."""
    p = doc.add_paragraph()
    _add_right_tab(p)
    _set_spacing(p, before=0, after=0)
    _base_run(p, role, italic=True)
    _base_run(p, "\t")
    _base_run(p, date)


def add_body(doc, text, space_before=0):
    p = doc.add_paragraph()
    _set_spacing(p, before=space_before, after=0)
    _base_run(p, text)


def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    _set_spacing(p, before=0, after=0)
    pf = p.paragraph_format
    pf.left_indent = Inches(0.2)
    pf.first_line_indent = Inches(-0.15)
    _base_run(p, text)


def add_skills_line(doc, label, value):
    p = doc.add_paragraph()
    _set_spacing(p, before=1, after=0)
    _base_run(p, label + ": ", bold=True)
    _base_run(p, value)


# ── ES document ────────────────────────────────────────────────────────────────

def build_es():
    doc = Document()
    _set_margins(doc)

    # remove default empty paragraph
    for p in doc.paragraphs:
        p._element.getparent().remove(p._element)

    add_name(doc, "Mickael Adrian Moran Vera")
    add_contact(
        doc,
        "Guayaquil, Ecuador  •  mickaelmoranvera03@gmail.com  •  +593 98 377 7036",
        "linkedin.com/in/mickaell-moran-vera-ba421a2a3  •  github.com/Mickaell22  •  mickaell.novamicktools.com",
    )

    # ── PERFIL ──
    add_section(doc, "Perfil")
    add_body(
        doc,
        "Desarrollador fullstack con sistemas en producción para clientes reales en Ecuador "
        "(gestión clínica, facturación electrónica SRI, inventario multisucursal). "
        "Especializado en Django/DRF y React/Next.js, con formación complementaria en ciberseguridad.",
    )

    # ── EXPERIENCIA ──
    # Experiencia va ANTES de Educación: el rol de cofundador y los sistemas en
    # producción pesan más que la etiqueta de "9no semestre".
    add_section(doc, "Experiencia")

    add_org_line(doc, "EcuaInventario", "Guayaquil, Ecuador")
    add_role_line(doc, "Co-fundador & Desarrollador Fullstack", "Feb. 2026 – presente")
    add_bullet(doc, "Desarrollé backend con Django 5 + DRF + PostgreSQL para plataforma SaaS multitenancy del sector gastronómico.")
    add_bullet(doc, "Integré asistente IA con Claude (Anthropic) para consultas de inventario, gestión de pedidos y reportes automáticos.")
    add_bullet(doc, "Construí app móvil con Flutter + Riverpod con sincronización en tiempo real vía Firebase.")
    add_bullet(doc, "Diseñé arquitectura multitenancy con aislamiento de datos por tenant y sistema de suscripción mensual.")

    add_org_line(doc, "Freelance", "Guayaquil, Ecuador", space_before=6)
    add_role_line(doc, "Desarrollador Fullstack", "Jul. 2025 – presente")
    add_bullet(doc, "Desarrollé sistema de gestión clínica Tia Glenda (React + MUI + Python + PostgreSQL, 190+ componentes) en producción.")
    add_bullet(doc, "Construí sistema de facturación electrónica integrado con el SRI de Ecuador, en producción en novamicktools.com.")
    add_bullet(doc, "Implementé SimuladorPreguntas universitario (React + FastAPI + PostgreSQL) con roles diferenciados y medidas anti-trampa.")
    add_bullet(doc, "Desarrollé Taller App: sistema de gestión para taller mecánico (Node.js + React), proyecto freelance completado.")

    add_org_line(doc, "Área de Nivelación — Universidad de Guayaquil", "Guayaquil, Ecuador", space_before=6)
    add_role_line(doc, "Practicante de Desarrollo de Software", "Feb. 2026 – Jul. 2026")
    add_bullet(doc, "Lideré el desarrollo frontend, backend, pruebas y deploy del SimuladorPreguntas para uso institucional.")
    add_bullet(doc, "Automaticé procesos internos de registro y generación de reportes mediante scripts Python.")

    # ── EDUCACIÓN ──
    add_section(doc, "Educación")

    add_org_line(doc, "Universidad de Guayaquil", "Guayaquil, Ecuador", space_before=4)
    add_role_line(doc, "Ingeniería en Software — 9no semestre (de 10)", "2021 – presente")
    add_body(doc, "Promedio académico: 9.01 / 10  (escala 0–10, aprobación desde 7)")

    add_org_line(doc, "Google / Coursera", "En línea", space_before=4)
    add_role_line(doc, "Certificado Profesional de Ciberseguridad", "2026 – en progreso")

    add_org_line(doc, "Google / Coursera", "En línea", space_before=4)
    add_role_line(doc, "Certificado Profesional de UX Design", "2026 – en progreso")

    add_org_line(doc, "Academia de Ciberseguridad Hacker Mentor", "En línea", space_before=4)
    add_role_line(doc, "Curso de Ethical Hacking — Red Team (8 horas)", "2023")

    # ── PROYECTOS ──
    add_section(doc, "Proyectos")

    add_org_line(doc, "MotoVox", "github.com/Mickaell22/MotoVox")
    add_role_line(doc, "App de comunicación por voz para motociclistas", "Flutter · C · WebRTC · FFI")
    add_bullet(doc, "Integré código C nativo con Flutter vía FFI para procesamiento de audio en tiempo real sin JVM overhead.")
    add_bullet(doc, "Implementé streaming de audio peer-to-peer vía WebRTC sin servidor intermediario.")

    add_org_line(doc, "QR Shield", "github.com/Mickaell22/qr-shield", space_before=6)
    add_role_line(doc, "Herramienta de seguridad para análisis de QR", "Python · Chrome Extension")
    add_bullet(doc, "Desarrollé extensión Chrome que intercepta escaneos de QR y consulta API Python para validar URLs maliciosas.")
    add_bullet(doc, "Construí API REST en Python con análisis de reputación de dominios y detección de phishing.")

    add_org_line(doc, "ApplyJob", "github.com/Mickaell22/ApplyJob", space_before=6)
    add_role_line(doc, "Pipeline de agregación y matching de ofertas con LLMs", "Python · Playwright · LLMs")
    add_bullet(doc, "Construí agregación de 7 fuentes heterogéneas (APIs JSON, RSS y HTML) normalizadas a un esquema común, con Playwright headless para las que requieren render JS.")
    add_bullet(doc, "Implementé matching semántico contra perfil y generación de texto con LLMs; reordenar el prompt para caché de prefijo redujo ~80% los tokens de entrada.")

    # ── HABILIDADES ──
    add_section(doc, "Habilidades")

    add_skills_line(doc, "Backend", "Python, Django, FastAPI, Node.js, Express, C#, Java")
    add_skills_line(doc, "Frontend", "React, Next.js, TypeScript, Tailwind CSS, Vite")
    add_skills_line(doc, "Móvil", "Flutter, Dart, Riverpod, Firebase")
    add_skills_line(doc, "Bases de datos", "PostgreSQL, SQLAlchemy, Alembic, Firebase Firestore, SQLite")
    add_skills_line(doc, "Herramientas", "Git, Docker, Linux, VPS (Railway), Cloudinary, Postman")
    add_skills_line(doc, "Ciberseguridad", "Kali Linux, Nmap, Wireshark, fundamentos de ethical hacking")
    add_skills_line(doc, "Idiomas", "Español (nativo), Inglés (B2 — lectura, escritura técnica y conversacional)")

    return doc


# ── EN document ────────────────────────────────────────────────────────────────

def build_en():
    doc = Document()
    _set_margins(doc)

    for p in doc.paragraphs:
        p._element.getparent().remove(p._element)

    add_name(doc, "Mickael Adrian Moran Vera")
    add_contact(
        doc,
        "Guayaquil, Ecuador  •  mickaelmoranvera03@gmail.com  •  +593 98 377 7036",
        "linkedin.com/in/mickaell-moran-vera-ba421a2a3  •  github.com/Mickaell22  •  mickaell.novamicktools.com",
    )

    # ── PROFILE ──
    add_section(doc, "Profile")
    add_body(
        doc,
        "Fullstack developer with systems running in production for real clients in Ecuador "
        "(clinical management, SRI e-invoicing, multi-branch inventory). "
        "Focused on Django/DRF and React/Next.js, with complementary training in cybersecurity.",
    )

    # ── EXPERIENCE ──
    add_section(doc, "Experience")

    add_org_line(doc, "EcuaInventario", "Guayaquil, Ecuador")
    add_role_line(doc, "Co-founder & Fullstack Developer", "Feb 2026 – present")
    add_bullet(doc, "Built backend with Django 5 + Django REST Framework + PostgreSQL for a multitenancy SaaS targeting the restaurant industry.")
    add_bullet(doc, "Integrated an AI assistant powered by Claude (Anthropic) for inventory queries, order management, and automated reports.")
    add_bullet(doc, "Developed mobile app with Flutter + Riverpod with real-time sync via Firebase.")
    add_bullet(doc, "Designed multitenancy architecture with per-tenant data isolation and monthly subscription billing.")

    add_org_line(doc, "Freelance", "Guayaquil, Ecuador", space_before=6)
    add_role_line(doc, "Fullstack Developer", "Jul 2025 – present")
    add_bullet(doc, "Built Tia Glenda clinical management system (React + MUI + Python + PostgreSQL, 190+ components) — in production.")
    add_bullet(doc, "Developed an e-invoicing system integrated with Ecuador's SRI tax authority, running in production at novamicktools.com.")
    add_bullet(doc, "Implemented university exam simulator (React + FastAPI + PostgreSQL) with role-based access and anti-cheating measures.")
    add_bullet(doc, "Delivered Taller App: workshop management system (Node.js + React) for a freelance client.")

    add_org_line(doc, "Leveling Area — University of Guayaquil", "Guayaquil, Ecuador", space_before=6)
    add_role_line(doc, "Software Development Intern", "Feb 2026 – Jul 2026")
    add_bullet(doc, "Led frontend, backend, testing, and deployment of the SimuladorPreguntas platform for institutional use.")
    add_bullet(doc, "Automated internal registration and report-generation workflows using Python scripts.")

    # ── EDUCATION ──
    add_section(doc, "Education")

    add_org_line(doc, "University of Guayaquil", "Guayaquil, Ecuador", space_before=4)
    add_role_line(doc, "B.Sc. Software Engineering — 9th semester (of 10)", "2021 – present")
    add_body(doc, "GPA: 9.01 / 10  (grading system: 0–10, minimum passing grade: 7)")

    add_org_line(doc, "Google / Coursera", "Online", space_before=4)
    add_role_line(doc, "Professional Certificate in Cybersecurity", "2026 – in progress")

    add_org_line(doc, "Google / Coursera", "Online", space_before=4)
    add_role_line(doc, "Professional Certificate in UX Design", "2026 – in progress")

    add_org_line(doc, "Hacker Mentor Cybersecurity Academy", "Online", space_before=4)
    add_role_line(doc, "Ethical Hacking — Red Team course (8 hours)", "2023")

    # ── PROJECTS ──
    add_section(doc, "Projects")

    add_org_line(doc, "MotoVox", "github.com/Mickaell22/MotoVox")
    add_role_line(doc, "Voice communication app for motorcycle riders", "Flutter · C · WebRTC · FFI")
    add_bullet(doc, "Integrated native C code with Flutter via FFI for real-time audio processing with no JVM overhead.")
    add_bullet(doc, "Implemented peer-to-peer audio streaming via WebRTC without an intermediary server.")

    add_org_line(doc, "QR Shield", "github.com/Mickaell22/qr-shield", space_before=6)
    add_role_line(doc, "Security tool for QR code analysis", "Python · Chrome Extension")
    add_bullet(doc, "Built a Chrome extension that intercepts QR scans and queries a Python API to validate URLs for malicious content.")
    add_bullet(doc, "Developed REST API in Python with domain reputation analysis and phishing detection.")

    add_org_line(doc, "ApplyJob", "github.com/Mickaell22/ApplyJob", space_before=6)
    add_role_line(doc, "Job posting aggregation and matching pipeline with LLMs", "Python · Playwright · LLMs")
    add_bullet(doc, "Built aggregation of 7 heterogeneous sources (JSON APIs, RSS, and HTML) normalized into a common schema, with headless Playwright for JS-rendered ones.")
    add_bullet(doc, "Implemented semantic matching against the candidate profile and LLM text generation; reordering the prompt for prefix caching cut input tokens by ~80%.")

    # ── SKILLS ──
    add_section(doc, "Skills")

    add_skills_line(doc, "Backend", "Python, Django, FastAPI, Node.js, Express, C#, Java")
    add_skills_line(doc, "Frontend", "React, Next.js, TypeScript, Tailwind CSS, Vite")
    add_skills_line(doc, "Mobile", "Flutter, Dart, Riverpod, Firebase")
    add_skills_line(doc, "Databases", "PostgreSQL, SQLAlchemy, Alembic, Firebase Firestore, SQLite")
    add_skills_line(doc, "Tools", "Git, Docker, Linux, VPS (Railway), Cloudinary, Postman")
    add_skills_line(doc, "Cybersecurity", "Kali Linux, Nmap, Wireshark, ethical hacking fundamentals")
    add_skills_line(doc, "Languages", "Spanish (native), English (B2 — reading, technical writing, conversational)")

    return doc


# ── main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pathlib

    out = pathlib.Path(__file__).parent

    # nombres que consumen CV_PATH / CV_PATH_EN del .env
    es_path = out / "cv_es.docx"
    en_path = out / "cv_en.docx"

    build_es().save(es_path)
    print(f"✓ {es_path}")

    build_en().save(en_path)
    print(f"✓ {en_path}")
