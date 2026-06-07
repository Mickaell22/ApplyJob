"""Compara una oferta contra el perfil del candidato y calcula compatibilidad."""

import re
from pathlib import Path


def load_profile(path: str = "profile/cv.md") -> dict:
    """Carga el perfil del candidato desde un archivo markdown."""
    p = Path(path)
    if not p.exists():
        return {"error": f"No se encontro {path}"}

    text = p.read_text()
    return {
        "full_text": text,
        "techs": _extract_list(text, r"(?:stack|skills|tecnologias)[:\s]*([\s\S]*?)(?:\n#|\n##|\Z)"),
    }


def score(job: dict, profile: dict) -> dict:
    """Evalua que tan compatible es una oferta con el perfil."""
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    keywords = [k.lower() for k in profile.get("techs", [])]

    matched = [k for k in keywords if k in text]
    score = round(len(matched) / max(len(keywords), 1) * 100, 1)

    return {
        "score": score,
        "matched_techs": matched,
        "fit": "alta" if score >= 40 else "media" if score >= 8 else "baja",
    }


def _extract_list(text: str, pattern: str) -> list[str]:
    match = re.search(pattern, text, re.I)
    if not match:
        return []
    raw = match.group(1)
    return re.findall(r"[A-Za-z#+]+(?:\.?\w+)*", raw)
