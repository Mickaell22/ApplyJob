"""Cimientos compartidos por todos los boards: headers, filtros y helpers HTTP."""

import json
import os
import re
import time
from urllib.parse import urlencode
import httpx
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "es,en;q=0.9",
}

TECH_FILTER = re.compile(
    r"\b(python|django|fastapi|flask|backend|back.?end|fullstack|full.?stack|"
    r"react|typescript|node\.?js|javascript|developer|engineer|software|"
    r"devops|cloud|linux|api|junior|graduate|trainee|data|qa|mobile|flutter|"
    r"desarrollador|programador)\b",
    re.I,
)

# Excluye títulos claramente senior/lead/architect para no perder tiempo
_SENIOR_EXCLUDE = re.compile(
    r"\b(senior|s[êe]nior|sr\.?|ssr|semi.?senior|intermedio|mid.?level|lead|architect|"
    r"principal|staff|manager|head\s+of|director|expert|experto|l[íi]der|"
    r"jefe|c\.?t\.?o|v\.?p\.?|founding)\b",
    re.I,
)

REMOTE_FILTER = re.compile(
    r"\b(remoto|remote|100%\s*remoto?|distributed|global)\b", re.I
)

# ---------------------------------------------------------------------------
# Geo filters — configurables via CANDIDATE_REGION en .env
# Opciones: LATAM (default), EUROPE, ASIA, USA, GLOBAL
# ---------------------------------------------------------------------------

_CANDIDATE_REGION = os.getenv("CANDIDATE_REGION", "LATAM").strip().upper()

_REGION_OK_TERMS = {
    "LATAM":  ["LATAM", "Latin America", "South America", "Americas", "not in the US", "not US"],
    "EUROPE": ["Europe", "European Union", "EU", "EMEA"],
    "ASIA":   ["Asia", "APAC", "Asia Pacific"],
    "USA":    ["United States", "North America", "Americas"],
    "GLOBAL": [],
}
_NON_LATAM_COUNTRIES = [
    # Europe
    "Germany", "France", "Spain", "Italy", "Poland", "Netherlands", "Belgium",
    "Sweden", "Norway", "Denmark", "Finland", "Austria", "Switzerland",
    "Czech Republic", "Hungary", "Romania", "Bulgaria", "Portugal", "Ireland",
    "Greece", "Ukraine", "Malta", "Serbia", "Bosnia", "Lithuania", "Latvia",
    "Estonia", "Croatia", "Slovakia", "Luxembourg", "United Kingdom",
    # Asia & Middle East
    "India", "China", "Japan", "South Korea", "Taiwan", "Philippines",
    "Indonesia", "Vietnam", "Thailand", "Malaysia", "Singapore", "Pakistan",
    "Bangladesh", "Saudi Arabia", "UAE", "United Arab Emirates", "Israel",
    "Turkey", "Sri Lanka",
    # Oceania
    "Australia", "New Zealand",
    # Africa
    "Nigeria", "South Africa", "Kenya", "Egypt",
    # North America (non-LATAM)
    "Canada",
]

_REGION_EXCL_TERMS = {
    "LATAM":  [
        "USA", "US only", "United States", "Europe only", "EU only",
        "Brazil only", "Mexico only", "Argentina only", "Colombia only",
    ] + _NON_LATAM_COUNTRIES,
    "EUROPE": ["USA", "US only", "United States", "LATAM only", "Latin America only",
               "India only", "Australia only"],
    "ASIA":   ["USA", "US only", "United States", "Europe only", "EU only",
               "LATAM only", "Latin America only"],
    "USA":    ["Europe only", "EU only", "LATAM only", "India only", "Australia only"],
    "GLOBAL": [],
}

_ok_terms   = ["Worldwide", "Anywhere", "Global", "International"] + _REGION_OK_TERMS.get(_CANDIDATE_REGION, _REGION_OK_TERMS["LATAM"])
_excl_terms = _REGION_EXCL_TERMS.get(_CANDIDATE_REGION, _REGION_EXCL_TERMS["LATAM"])

# NO incluir "Remote" suelto — "Japan - Remote" lo matchearía como falso positivo
_LOCATION_OK      = re.compile(r"\b(" + "|".join(_ok_terms)   + r")\b", re.I)
_LOCATION_EXCLUDE = re.compile(r"\b(" + "|".join(_excl_terms) + r")\b", re.I) if _excl_terms else re.compile(r"(?!x)")


# ---------------------------------------------------------------------------
# Filtro geo-global reutilizable
# ---------------------------------------------------------------------------

def filter_global_remote(jobs: list[dict]) -> list[dict]:
    """Filtra jobs por accesibilidad según CANDIDATE_REGION en .env.

    - Sin location_required → pasa
    - Worldwide/Anywhere/Global o región del candidato → pasa
    - Región incompatible (ej. USA only para candidato LATAM) → excluye
    - Ambiguo (ciudad, región parcial) → pasa con flag location_warning
    """
    result = []
    for job in jobs:
        loc = job.get("location_required", "") or ""
        if not loc.strip():
            result.append(job)
            continue
        if _LOCATION_OK.search(loc):
            result.append(job)
            continue
        if _LOCATION_EXCLUDE.search(loc):
            continue
        # Ambiguo → incluir con advertencia visible al usuario
        job["location_warning"] = loc
        result.append(job)
    return result


# ---------------------------------------------------------------------------
# Filtros de titulo/experiencia + verificacion de vigencia
# ---------------------------------------------------------------------------

def filter_tech(jobs: list[dict]) -> list[dict]:
    """Filtra ofertas relevantes por keywords técnicas en el título."""
    return [j for j in jobs if TECH_FILTER.search(j.get("title", ""))]


def filter_junior(jobs: list[dict]) -> list[dict]:
    """Excluye ofertas claramente senior/lead/architect.

    Deja pasar: junior, trainee, pasante, practica, graduate, mid, y sin nivel
    explícito. Así aparecen las que pueden funcionar para primer empleo.
    """
    return [j for j in jobs if not _SENIOR_EXCLUDE.search(j.get("title", ""))]


# Descripción requiere 3+ años → descarta (ej. "3 años de experiencia", "mínimo 4 años")
_EXP_EXCLUDE = re.compile(
    r"(?:m[íi]nimo|m[íi]nima|al\s+menos|m[áa]s\s+de|experiencia\s+de|"
    r"experiencia\s+m[íi]nima\s+de|requiere)\s+[3-9]\d*\s*(?:años?|years?)|"
    r"\b[3-9]\+?\s*(?:años?|years?)\s+(?:de\s+)?experiencia",
    re.I,
)


def filter_entry_level(jobs: list[dict]) -> list[dict]:
    """Descarta ofertas cuya descripción pide 3+ años de experiencia.

    Si la descripción está vacía o no menciona años requeridos, pasa igual.
    """
    result = []
    for job in jobs:
        desc = job.get("description", "")
        # Quitar HTML antes de analizar
        desc_text = re.sub(r"<[^>]+>", " ", desc)
        if _EXP_EXCLUDE.search(desc_text):
            continue
        result.append(job)
    return result


_NOISE_TITLE_EXCLUDE = re.compile(
    r"\b(?:devops\s+engineer|junior\s+devops|devops\s+virtual|network\s+devops\s+engineer|"
    r"devops\s+e\s+platform|engenheiro\s+devops|pessoa\s+engenheira\s+de\s+devops|"
    r"devsecops\s+engineer|site\s+reliability\s+engineer|"
    r"qa\s+engineer|quality\s+assurance\s+engineer|quality\s+automation\s+engineer|"
    r"automation\s+tester|manual\s+qa|"
    r"sales\s+engineer|support\s+engineer|"
    r"data\s+engineer|"
    r"trading\s+operations\s+engineer|finops\s+analyst|"
    r"field\s+service\s+technician|systems?\s+administrator)\b",
    re.I,
)


def filter_role_noise(jobs: list[dict]) -> list[dict]:
    """Excluye roles fuera del stack del candidato (DevOps puro, QA, Sales, SRE, etc.)."""
    return [j for j in jobs if not _NOISE_TITLE_EXCLUDE.search(j.get("title", ""))]


def dedup_by_company_title(jobs: list[dict]) -> list[dict]:
    """Elimina duplicados por (empresa, título) — ej: Mindrift mismo job en 10 países."""
    seen: set[tuple] = set()
    result = []
    for job in jobs:
        key = (
            re.sub(r"\s+", " ", (job.get("company") or "").lower().strip()),
            re.sub(r"\s+", " ", (job.get("title") or "").lower().strip()),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(job)
    return result


# Marcadores de oferta muerta/cerrada en la pagina del job (EN + ES)
_DEAD_MARKERS = re.compile(
    r"no longer accepting applications|no longer available|no longer active|"
    r"position has been filled|job has expired|job posting (?:has )?(?:closed|expired)|"
    r"this (?:job|position|posting) (?:is|was) closed|"
    r"esta oferta (?:ha expirado|ya no|est[áa] cerrada)|oferta.{0,30}(?:expirad|cerrad|finalizad)|"
    r"ya no est[áa] disponible|postulaciones cerradas|vacante cerrada",
    re.I,
)


def is_job_dead(url: str) -> bool:
    """Verifica si una oferta sigue viva (para --verify en run_discover).

    ponytail: heuristica — 404/410 o un marcador de texto conocido = muerta;
    si no se puede verificar (bloqueo, timeout) se asume viva para no
    descartar por error. Techo: ATS con wording raro se escapan; se agregan
    marcadores a _DEAD_MARKERS cuando aparezcan.
    """
    try:
        r = httpx.get(url, headers=_HEADERS, follow_redirects=True, timeout=15)
        if r.status_code in (404, 410):
            return True
        html = r.text
    except Exception:
        html = _playwright_get(url) or ""
        if not html:
            return False  # no verificable -> asumir viva
    return bool(_DEAD_MARKERS.search(html))


# ---------------------------------------------------------------------------
# Helpers HTTP (httpx + Playwright fallback)
# ---------------------------------------------------------------------------

def _http_get(url: str) -> str | None:
    try:
        r = httpx.get(url, headers=_HEADERS, follow_redirects=True, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception:
        return None


def _playwright_get(url: str, wait_ms: int = 3000) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(user_agent=_HEADERS["User-Agent"])
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(wait_ms)
            html = page.content()
            browser.close()
        return html
    except Exception:
        return None


__all__ = [
    '_HEADERS',
    'TECH_FILTER',
    '_SENIOR_EXCLUDE',
    'REMOTE_FILTER',
    '_CANDIDATE_REGION',
    '_REGION_OK_TERMS',
    '_NON_LATAM_COUNTRIES',
    '_REGION_EXCL_TERMS',
    '_ok_terms',
    '_excl_terms',
    '_LOCATION_OK',
    '_LOCATION_EXCLUDE',
    'filter_global_remote',
    'filter_tech',
    'filter_junior',
    '_EXP_EXCLUDE',
    'filter_entry_level',
    '_NOISE_TITLE_EXCLUDE',
    'filter_role_noise',
    'dedup_by_company_title',
    '_DEAD_MARKERS',
    'is_job_dead',
    '_http_get',
    '_playwright_get',
]
