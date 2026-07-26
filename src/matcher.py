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
    return {"full_text": text, "techs": _extract_techs(text)}


def score(job: dict, profile: dict) -> dict:
    """Evalua que tan compatible es una oferta con el perfil."""
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    keywords = [k.lower() for k in profile.get("techs", [])]

    # Limite de palabra: con substring puro "ci" matchea "efficient" y "java"
    # matchea "javascript", inflando el score con ofertas que no son del stack.
    matched = [k for k in keywords if re.search(rf"(?<!\w){re.escape(k)}(?!\w)", text)]
    # Frameworks adyacentes (Vue/Angular/etc.): suman como senal para un dev React,
    # pero NO al denominador, para no descartar juniors front-end de otro framework.
    adjacent = [k for k in ADJACENT_TECHS if k in text and k not in matched]
    hits = len(matched) + len(adjacent)
    score = round(hits / max(len(keywords), 1) * 100, 1)

    return {
        "score": score,
        "matched_techs": matched + adjacent,
        # El fit va por CANTIDAD de coincidencias, no por %: el denominador es el
        # CV entero, asi que ampliar el stack bajaba el % de la misma oferta y
        # descalibraba los umbrales. 6 techs = claramente del stack; 2 = senal.
        "fit": "alta" if hits >= 6 else "media" if hits >= 2 else "baja",
    }


def _extract_techs(text: str) -> list[str]:
    """Tecnologias listadas en las secciones Stack/Skills del CV.

    El encabezado va anclado a inicio de linea a proposito: sin el ancla, el
    "Desarrollador fullstack" del Perfil matchea primero y se extraen las
    palabras de esa frase ("en", "y", "de") como si fueran tecnologias.
    """
    blocks = re.findall(
        r"^#{1,4}[ \t]*(?:stack|skills|tecnolog\w+)[ \t]*$\n([\s\S]*?)(?=^#|\Z)",
        text,
        re.I | re.M,
    )
    techs = []
    for line in "\n".join(blocks).splitlines():
        label, sep, rest = line.partition(":")
        if sep and label.strip("* ").lower() in ("idiomas", "languages"):
            continue
        # ponytail: el CV lista el stack separado por comas y las barras son
        # pares ("Django/DRF"); los parentesis son aclaraciones, no techs.
        for tok in re.split(r"[,/]", re.sub(r"\(.*?\)|\*+", "", rest if sep else line)):
            tok = tok.strip(" .")
            if 2 <= len(tok) <= 30 and re.match(r"[A-Za-z]", tok):
                techs.append(tok)
    return list(dict.fromkeys(techs))
