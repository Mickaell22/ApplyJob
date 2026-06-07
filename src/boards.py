"""Descubre ofertas laborales desde tableros de trabajo.

Boards soportados:
- getonbrd  : GetOnBrd LATAM  (getonbrd.com)  — API JSON + fallback HTML
- remotive  : Remotive.io     (remotive.com)  — API JSON pública, global remote
- glovo     : Glovo Careers   (careers.glovoapp.com) — Playwright
"""

import re
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
    r"devops|cloud|linux|api|junior|graduate|trainee|data|qa|mobile|flutter)\b",
    re.I,
)

# Excluye títulos claramente senior/lead/architect para no perder tiempo
_SENIOR_EXCLUDE = re.compile(
    r"\b(senior|sr\.?|ssr|semi.?senior|intermedio|mid.?level|lead|architect|"
    r"principal|staff|manager|head\s+of|director|expert|experto|l[íi]der|"
    r"jefe|c\.?t\.?o|v\.?p\.?|founding)\b",
    re.I,
)

REMOTE_FILTER = re.compile(
    r"\b(remoto|remote|100%\s*remoto?|distributed|global)\b", re.I
)


# ---------------------------------------------------------------------------
# GetOnBrd
# ---------------------------------------------------------------------------

def discover_getonbrd(remote_only: bool = True, max_pages: int = 3) -> list[dict]:
    """Descubre ofertas en getonbrd.com.

    Intenta primero la API JSON; si falla usa scraping HTML.
    """
    jobs = _getonbrd_api(remote_only, max_pages)
    if jobs:
        return jobs
    return _getonbrd_html(remote_only, max_pages)


def _getonbrd_api(remote_only: bool, max_pages: int) -> list[dict]:
    """Llama a la API pública de getonbrd (v0).

    La API devuelve formato JSON:API:
    - URL del job en item["links"]["self"]
    - Nombre de empresa en payload["included"] (type=company), referenciada por relationship
    """
    base = "https://www.getonbrd.com/api/v0/categories/programming/jobs"
    jobs: list[dict] = []
    try:
        for page in range(1, max_pages + 1):
            r = httpx.get(
                base,
                params={"page": page, "per_page": 50},
                headers={**_HEADERS, "Accept": "application/json"},
                timeout=15,
            )
            if r.status_code != 200:
                break
            payload = r.json()
            items = payload.get("data", []) if isinstance(payload, dict) else payload
            if not items:
                break

            # Construir mapa id→nombre de empresa desde "included"
            company_map: dict[int | str, str] = {}
            for inc in payload.get("included", []):
                if inc.get("type") == "company":
                    cid = inc.get("id")
                    cname = inc.get("attributes", {}).get("name", "")
                    if cid and cname:
                        company_map[cid] = cname

            for item in items:
                attrs = item.get("attributes", {}) if isinstance(item, dict) else {}
                title = attrs.get("title", "")
                remote = bool(attrs.get("remote_modality") or attrs.get("remote", False))
                if remote_only and not remote:
                    continue

                # Filtrar por seniority: 4=Senior, 5=Lead/Head
                # Dejar pasar junior (2), semi-senior (3) y sin nivel (None/1)
                seniority_id = (
                    attrs.get("seniority", {}).get("data", {}).get("id")
                )
                if seniority_id in (4, 5):
                    continue

                # URL canónica: links.public_url
                url = item.get("links", {}).get("public_url", "")

                # Empresa: no viene directamente en la API (relación sin include);
                # se llenará al scrapear la descripción completa.
                jobs.append({
                    "title": title,
                    "company": "",
                    "url": url,
                    "remote": remote,
                    "source": "getonbrd",
                    "description": attrs.get("description", ""),
                })
    except Exception:
        return []
    return jobs


def _getonbrd_html(remote_only: bool, max_pages: int) -> list[dict]:
    """Fallback: scraping HTML de getonbrd.com/jobs/programming."""
    base = "https://www.getonbrd.com"
    jobs: list[dict] = []
    seen: set[str] = set()

    for page in range(1, max_pages + 1):
        url = f"{base}/jobs/programming?page={page}"
        if remote_only:
            url += "&remote=true"

        html = _http_get(url) or _playwright_get(url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        found = 0
        for a in soup.find_all("a", href=re.compile(r"/jobs/[^/]+/[^/]+")):
            href = a.get("href", "")
            full_url = href if href.startswith("http") else base + href
            if full_url in seen:
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            seen.add(full_url)
            jobs.append({
                "title": title,
                "company": "",
                "url": full_url,
                "remote": True,
                "source": "getonbrd",
                "description": "",
            })
            found += 1

        if found == 0:
            break

    return jobs


# ---------------------------------------------------------------------------
# Remotive.io
# ---------------------------------------------------------------------------

# Excluye jobs con location_required explícitamente restringida a países sin Ecuador
_LOCATION_EXCLUDE = re.compile(
    r"\b(USA|US only|United States|UK only|United Kingdom|Europe only|"
    r"EU only|Canada only|Australia only|Brazil only|Mexico only|"
    r"Argentina only|Colombia only|India only)\b",
    re.I,
)

# Locations que confirman acceso desde Ecuador/LATAM
_LOCATION_OK = re.compile(
    r"\b(Worldwide|Anywhere|Global|LATAM|Latin America|South America|"
    r"Remote|Americas|International)\b",
    re.I,
)


def discover_remotive(category: str = "software-dev") -> list[dict]:
    """Descubre ofertas en remotive.com via API pública (sin auth).

    NOTA 2026-06-07: Remotive limitó su API gratuita a ~28 jobs fijos.
    Mantenida como fallback por si amplían el tier gratuito.
    """
    try:
        r = httpx.get(
            "https://remotive.com/api/remote-jobs",
            params={"category": category, "limit": 100},
            headers={**_HEADERS, "Accept": "application/json"},
            timeout=20,
        )
        r.raise_for_status()
        jobs = []
        for item in r.json().get("jobs", []):
            jobs.append({
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "url": item.get("url", ""),
                "remote": True,
                "source": "remotive",
                "description": item.get("description", ""),
                "location_required": item.get("candidate_required_location", "Worldwide"),
            })
        return jobs
    except Exception:
        return []


# ---------------------------------------------------------------------------
# RemoteOK
# ---------------------------------------------------------------------------

# Tags tech a consultar en RemoteOK (cada tag = 1 llamada API, se deduplica)
_REMOTEOK_TAGS = ["python", "react", "backend", "javascript", "mobile"]

# Excluye jobs cuya location es claramente país específico sin Ecuador
_REMOTEOK_LOC_EXCLUDE = re.compile(
    r"\b(United States|United Kingdom|Australia|Germany|France|"
    r"India|Brazil|Poland|Ukraine|Israel)\b",
    re.I,
)


def discover_remoteok() -> list[dict]:
    """Descubre ofertas en remoteok.com via API JSON pública (sin auth).

    Hace una llamada por tag tech, deduplica por slug, retorna jobs únicos.
    Location vacía = accesible desde cualquier país.
    """
    seen: set[str] = set()
    jobs: list[dict] = []

    for tag in _REMOTEOK_TAGS:
        try:
            r = httpx.get(
                f"https://remoteok.com/api?tag={tag}",
                headers={**_HEADERS, "User-Agent": _HEADERS["User-Agent"]},
                timeout=15,
            )
            if r.status_code != 200:
                continue
            for item in r.json():
                if not isinstance(item, dict) or not item.get("slug"):
                    continue
                slug = item["slug"]
                if slug in seen:
                    continue
                seen.add(slug)
                location = item.get("location", "") or ""
                jobs.append({
                    "title": item.get("position", ""),
                    "company": item.get("company", ""),
                    "url": item.get("url", f"https://remoteok.com/remote-jobs/{slug}"),
                    "remote": True,
                    "source": "remoteok",
                    "description": item.get("description", ""),
                    "location_required": location,
                    "tags": item.get("tags", []),
                })
        except Exception:
            continue

    # Deduplicar por (title, company) para evitar doble-posteo de misma posición
    final: list[dict] = []
    seen_tc: set[tuple] = set()
    for job in jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key in seen_tc:
            continue
        seen_tc.add(key)
        final.append(job)
    return final


def filter_global_remote(jobs: list[dict]) -> list[dict]:
    """Filtra jobs por accesibilidad desde Ecuador.

    - Sin location_required → pasa (ej. GetOnBrd nativo, RemoteOK sin ciudad)
    - Worldwide/Anywhere/LATAM/Global/Americas → pasa
    - USA only / UK only / etc. → excluye
    - Ambiguo (North America, Europe, ciudad) → pasa con flag location_warning
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
        if _LOCATION_EXCLUDE.search(loc) or _REMOTEOK_LOC_EXCLUDE.search(loc):
            continue
        # Ambiguo → incluir con advertencia visible al usuario
        job["location_warning"] = loc
        result.append(job)
    return result


# ---------------------------------------------------------------------------
# Glovo Careers
# ---------------------------------------------------------------------------

def discover_glovo(tech_only: bool = True) -> list[dict]:
    """Descubre ofertas tech en careers.glovoapp.com."""
    # Glovo usa Greenhouse; la board pública suele estar en:
    # https://careers.glovoapp.com/jobs/ o https://boards.greenhouse.io/glovo
    jobs: list[dict] = []
    seen: set[str] = set()

    sources = [
        "https://careers.glovoapp.com/jobs/",
        "https://boards.greenhouse.io/glovo",
    ]

    for list_url in sources:
        html = _http_get(list_url) or _playwright_get(list_url, wait_ms=4000)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Greenhouse board: cada oferta está en <a class="posting-title">
        # Fallback: cualquier <a> con /job/ o /opening/ en el href
        candidates = (
            soup.find_all("a", class_=re.compile(r"posting.title|job.title|opening", re.I))
            or soup.find_all("a", href=re.compile(r"/(job|opening|position)s?/", re.I))
        )

        for a in candidates:
            href = a.get("href", "")
            if not href:
                continue
            full_url = (
                href if href.startswith("http")
                else "https://careers.glovoapp.com" + href
            )
            if full_url in seen:
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            if tech_only and not TECH_FILTER.search(title):
                continue
            seen.add(full_url)
            jobs.append({
                "title": title,
                "company": "Glovo",
                "url": full_url,
                "remote": None,  # se verifica al scrapear el detalle
                "source": "glovo",
                "description": "",
            })

        if jobs:  # si una fuente da resultados, no seguir con la siguiente
            break

    return jobs


# ---------------------------------------------------------------------------
# Helpers
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


def getonbrd_apply_url(job_url: str) -> str:
    """Devuelve la URL de aplicación de GetOnBrd para un job dado."""
    return job_url.rstrip("/") + "/applications/new"


def resolve_apply_url(getonbrd_url: str) -> str | None:
    """Extrae la URL directa del ATS desde una página de getonbrd.

    GetOnBrd usa JavaScript para el botón "Postular" — usa Playwright para
    interceptar la petición de navegación o el popup que abre el ATS.
    """
    _ATS_DOMAINS = [
        "workable.com", "greenhouse.io", "teamtailor.com",
        "ashbyhq.com", "lever.co", "breezy.hr", "myworkdayjobs",
    ]

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context()
            page = context.new_page()

            # Interceptar cualquier request a dominios ATS
            captured: list[str] = []

            def _on_request(req):
                if any(d in req.url for d in _ATS_DOMAINS):
                    captured.append(req.url)

            page.on("request", _on_request)

            page.goto(getonbrd_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2000)

            # Primero revisar si el href ya está en el HTML (casos simples)
            for a in page.query_selector_all("a[href]"):
                href = a.get_attribute("href") or ""
                if any(d in href for d in _ATS_DOMAINS):
                    browser.close()
                    return href

            # Buscar botón "Postular" / "Apply" y hacer click
            for selector in [
                "a:has-text('Postular')", "button:has-text('Postular')",
                "a:has-text('Apply')",    "button:has-text('Apply')",
                "a:has-text('Solicitar')",
            ]:
                btn = page.query_selector(selector)
                if not btn:
                    continue
                try:
                    # Si abre un popup/nueva pestaña lo capturamos
                    with context.expect_page(timeout=5000) as popup_info:
                        btn.click()
                    popup = popup_info.value
                    popup.wait_for_load_state("domcontentloaded", timeout=8000)
                    url = popup.url
                    browser.close()
                    if any(d in url for d in _ATS_DOMAINS):
                        return url
                    return url  # devolver igual, puede ser útil
                except Exception:
                    # Sin popup → la navegación fue en la misma pestaña
                    page.wait_for_timeout(2000)
                    url = page.url
                    if any(d in url for d in _ATS_DOMAINS):
                        browser.close()
                        return url
                    break

            browser.close()
            # Último recurso: algún request interceptado
            return captured[0] if captured else None

    except Exception:
        return None


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
