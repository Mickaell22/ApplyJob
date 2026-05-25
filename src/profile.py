"""Carga, parsea y provee el perfil del candidato."""

from pathlib import Path
import re


def load(path: str = "profile/cv.md") -> dict:
    """Carga el perfil markdown y extrae secciones estructuradas."""
    p = Path(path)
    if not p.exists():
        return {"error": f"No se encontro {p.resolve()}"}

    raw = p.read_text(encoding="utf-8")

    sections = {}
    current = "__header__"
    lines = raw.split("\n")
    for line in lines:
        if line.startswith("##"):
            current = line.strip("# ")
            sections[current] = ""
        else:
            sections.setdefault(current, "")
            sections[current] += line + "\n"

    return {
        "raw": raw,
        "sections": sections,
        "techs": _parse_techs(raw),
        "name": _parse_name(raw),
        "email": _parse_email(raw),
    }


def _parse_techs(text: str) -> list[str]:
    techs = set()
    for word in re.findall(r"(?:Python|Django|FastAPI|Flask|React|Next\.?js|TypeScript|JavaScript|Node\.?js|Express|Flutter|Dart|PostgreSQL|Docker|Linux|Git|Firebase|Tailwind|Vite|REST|API|GraphQL|SQLAlchemy|Alembic|C#|Java|Nmap|Metasploit|Wireshark)", text, re.I):
        techs.add(word.lower())
    return sorted(techs)


def _parse_name(text: str) -> str:
    m = re.search(r"^#\s+(.+)", text, re.M)
    return m.group(1).strip() if m else "Candidato"


def _parse_email(text: str) -> str | None:
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    return m.group(0) if m else None
