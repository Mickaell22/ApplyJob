"""Compara una oferta contra el perfil del candidato y calcula compatibilidad."""

import re
from pathlib import Path

# Frameworks/tecnologias adyacentes al stack del candidato (React/JS/TS).
# Un junior con React asume Vue/Angular/etc. rapido, asi que cuentan como senal
# de RELEVANCIA (no de dominio) para no descartar esos roles junior. Solo suman
# al numerador; el denominador sigue siendo el CV real (no infla el % a lo bobo).
ADJACENT_TECHS = ["vue", "angular", "svelte", "nextjs", "nuxt"]


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
    # Frameworks adyacentes (Vue/Angular/etc.): suman como senal para un dev React,
    # pero NO al denominador, para no descartar juniors front-end de otro framework.
    adjacent = [k for k in ADJACENT_TECHS if k in text and k not in matched]
    hits = len(matched) + len(adjacent)
    score = round(hits / max(len(keywords), 1) * 100, 1)

    return {
        "score": score,
        "matched_techs": matched + adjacent,
        "fit": "alta" if score >= 40 else "media" if score >= 8 else "baja",
    }


def _extract_list(text: str, pattern: str) -> list[str]:
    match = re.search(pattern, text, re.I)
    if not match:
        return []
    raw = match.group(1)
    return re.findall(r"[A-Za-z#+]+(?:\.?\w+)*", raw)
