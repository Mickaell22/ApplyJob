"""Self-check del matcher. Correr: .venv/bin/python3 tests/test_matcher.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import matcher  # noqa: E402

CV = """# Nombre

## Perfil

Desarrollador fullstack con sistemas en produccion, especializado en Django y React.

## Stack

Python, Django/DRF, React, PostgreSQL, Docker, Java

## Skills

**Backend:** Python, FastAPI
**Idiomas:** Español (nativo), Inglés (B2 — lectura, escritura técnica)

## Educacion

Ingenieria en Software
"""


def test_extraccion(tmp: Path):
    tmp.write_text(CV)
    techs = matcher.load_profile(str(tmp))["techs"]

    # El "fullstack" del Perfil no debe arrastrar esa frase como si fuera stack.
    for basura in ("con", "en", "y", "de", "Desarrollador", "sistemas"):
        assert basura not in techs, f"palabra del Perfil extraida como tech: {basura}"

    assert "Python" in techs and "PostgreSQL" in techs, techs
    assert "Django" in techs and "DRF" in techs, f"la barra debe separar pares: {techs}"
    assert "FastAPI" in techs, f"la seccion Skills tambien cuenta: {techs}"
    assert not any("Español" in t or "nativo" in t for t in techs), techs
    assert len(techs) == len(set(techs)), f"hay duplicados: {techs}"


def test_score(tmp: Path):
    perfil = matcher.load_profile(str(tmp))

    alta = matcher.score(
        {"title": "Junior Backend Developer",
         "description": "Python, Django, DRF, React, PostgreSQL, Docker"}, perfil)
    assert alta["fit"] == "alta", alta

    # Framework adyacente: cuenta como senal aunque no este en el CV.
    vue = matcher.score({"title": "Vue Developer", "description": "Vue, Nuxt"}, perfil)
    assert vue["matched_techs"] == ["vue", "nuxt"], vue
    assert vue["fit"] == "media", vue

    ajeno = matcher.score(
        {"title": "Salesforce Consultant",
         "description": "Apex and Visualforce, efficient communication"}, perfil)
    assert ajeno["fit"] == "baja", ajeno
    # "efficient" no debe matchear "ci"; "javascript" no debe matchear "java".
    assert ajeno["matched_techs"] == [], ajeno
    js = matcher.score({"title": "Dev", "description": "javascript only"}, perfil)
    assert "java" not in js["matched_techs"], js


if __name__ == "__main__":
    tmp = Path(__file__).with_name("_cv_fixture.md")
    try:
        test_extraccion(tmp)
        test_score(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    print("OK — matcher")
