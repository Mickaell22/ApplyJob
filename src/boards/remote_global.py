"""Boards remoto-global via API/RSS/Playwright: GetOnBrd, Remotive, WWR, 4DayWeek, RemoteFirstJobs, WorkingNomads, Himalayas, Wellfound, Glovo, Hacker News."""

import json
import os
import re
import time
from urllib.parse import urlencode
import httpx
from bs4 import BeautifulSoup
from ._common import *  # noqa: F401,F403


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
# _LOCATION_OK y _LOCATION_EXCLUDE definidos en el bloque de geo-filters arriba


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
# We Work Remotely (weworkremotely.com)
# ---------------------------------------------------------------------------

_WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
]


def discover_weworkremotely() -> list[dict]:
    """Descubre ofertas en weworkremotely.com via RSS público (sin auth).

    Parsea feeds de Programming, Full-Stack y DevOps/SysAdmin.
    Campo <region> del item RSS → location_required para filter_global_remote.
    Título formato "Company: Job Title" → separa empresa y puesto.
    """
    from xml.etree import ElementTree as ET

    seen: set[str] = set()
    jobs: list[dict] = []

    for feed_url in _WWR_FEEDS:
        try:
            r = httpx.get(feed_url, headers=_HEADERS, timeout=15)
            r.raise_for_status()
            root = ET.fromstring(r.text)

            for item in root.findall(".//item"):
                guid = (item.findtext("guid") or "").strip()
                if not guid or guid in seen:
                    continue

                title_raw = (item.findtext("title") or "").strip()
                if ": " in title_raw:
                    company, title = title_raw.split(": ", 1)
                else:
                    company, title = "", title_raw

                region = (item.findtext("region") or "Worldwide").strip()
                link   = (item.findtext("link")   or "").strip()
                desc   = (item.findtext("description") or "").strip()

                seen.add(guid)
                jobs.append({
                    "title":             title,
                    "company":           company,
                    "url":               link,
                    "remote":            True,
                    "source":            "weworkremotely",
                    "description":       desc,
                    "location_required": region,
                })
        except Exception:
            continue

    return jobs


# ---------------------------------------------------------------------------
# 4 Day Week (4dayweek.io)
# ---------------------------------------------------------------------------

_4DW_API = "https://4dayweek.io/api/v2/jobs"


def discover_4dayweek(max_pages: int = 6) -> list[dict]:
    """Descubre ofertas en 4dayweek.io via API pública (sin auth).

    Filtra por work_arrangement=remote y level=entry,mid.
    El campo url apunta a la página del job en 4dayweek.io donde el candidato
    puede ver los detalles y hacer click en Apply.
    """
    seen: set[str] = set()
    jobs: list[dict] = []

    for page in range(1, max_pages + 1):
        try:
            r = httpx.get(
                _4DW_API,
                params={"work_arrangement": "remote", "level": "entry,mid", "page": page},
                headers={**_HEADERS, "Accept": "application/json"},
                timeout=15,
            )
            r.raise_for_status()
            data   = r.json()
            items  = data.get("data", [])
            if not items:
                break

            for item in items:
                job_id = item.get("id", "")
                if not job_id or job_id in seen:
                    continue

                # Extraer ubicación primaria para filter_global_remote
                locs = item.get("locations") or []
                primary = next((l for l in locs if l.get("is_primary")), locs[0] if locs else {})
                country = primary.get("country", "") or ""

                seen.add(job_id)
                jobs.append({
                    "title":             item.get("title", ""),
                    "company":           (item.get("company") or {}).get("name", ""),
                    "url":               item.get("url", ""),
                    "remote":            True,
                    "source":            "4dayweek",
                    "description":       item.get("description", ""),
                    "location_required": country,
                })

            if not data.get("has_more"):
                break
        except Exception:
            break

    return jobs


# ---------------------------------------------------------------------------
# Remote First Jobs (remotefirstjobs.com)
# ---------------------------------------------------------------------------

_RFJ_API  = "https://remotefirstjobs.com/api/search-jobs"
_RFJ_SENIORITY_OK = {"entry_level", "middle", "intern"}
_RFJ_QUERIES = ["developer", "engineer", "backend", "fullstack", "python", "react"]


def discover_remotefirstjobs(max_pages: int = 2) -> list[dict]:
    """Descubre ofertas en remotefirstjobs.com via API pública.

    Consulta múltiples keywords tech. Filtra entry_level e intern por seniority.
    Max 100 jobs/página; API gratuita limita a 5 páginas y 24h de delay.
    El campo url apunta a la página del job en remotefirstjobs.com.
    """
    seen: set[str] = set()
    jobs: list[dict] = []

    for query in _RFJ_QUERIES:
        for page in range(1, max_pages + 1):
            try:
                r = httpx.get(
                    _RFJ_API,
                    params={"query": query, "page": page},
                    headers={**_HEADERS, "Accept": "application/json"},
                    timeout=20,
                )
                r.raise_for_status()
                data  = r.json()
                items = data.get("jobs", [])
                if not items:
                    break

                for item in items:
                    job_id = item.get("id", "")
                    if not job_id or job_id in seen:
                        continue

                    seniority = (item.get("seniority") or "").lower()
                    if seniority and seniority not in _RFJ_SENIORITY_OK:
                        continue

                    locs = item.get("locations") or []
                    location = ", ".join(locs) if locs else ""

                    seen.add(job_id)
                    jobs.append({
                        "title":             item.get("title", ""),
                        "company":           item.get("company_name", ""),
                        "url":               item.get("url", ""),
                        "remote":            True,
                        "source":            "remotefirstjobs",
                        "description":       item.get("description", ""),
                        "location_required": location,
                    })

                if len(items) < 100:
                    break
            except Exception:
                break

    return jobs


# ---------------------------------------------------------------------------
# Working Nomads (workingnomads.com)
# ---------------------------------------------------------------------------

_WN_CATEGORIES = ["programming", "devops-sysadmin"]


def discover_workingnomads() -> list[dict]:
    """Descubre ofertas en workingnomads.com via API pública (sin auth).

    Consulta las categorías programming y devops-sysadmin.
    Campos de respuesta: url, title, description, company_name, location, pub_date, tags.
    La url apunta a workingnomads.com/job/go/<id>/ que redirige al ATS de la empresa.
    El campo location se usa para filtro de país (filter_global_remote).
    """
    seen: set[str] = set()
    jobs: list[dict] = []

    for cat in _WN_CATEGORIES:
        try:
            r = httpx.get(
                "https://www.workingnomads.com/api/exposed_jobs/",
                params={"category": cat},
                headers={**_HEADERS, "Accept": "application/json"},
                timeout=20,
            )
            r.raise_for_status()
            for item in r.json():
                apply_url = item.get("url", "").strip()
                if not apply_url or apply_url in seen:
                    continue
                seen.add(apply_url)

                location = (item.get("location") or "").strip()

                jobs.append({
                    "title":             item.get("title", ""),
                    "company":           item.get("company_name", ""),
                    "url":               apply_url,
                    "remote":            True,
                    "source":            "workingnomads",
                    "description":       item.get("description", ""),
                    "location_required": location,
                })
        except Exception:
            continue

    return jobs


# ---------------------------------------------------------------------------
# Himalayas.app
# ---------------------------------------------------------------------------

_HIMALAYAS_QUERIES = ["python", "react", "fullstack", "backend", "javascript", "developer"]

# Himalayas bloquea Accept-Language; usar solo User-Agent + Accept
_HIMALAYAS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Himalayas usa nombres de país directos (sin "only") → patrones separados por región
_HIMALAYAS_OK_TERMS = {
    "LATAM":  ["Worldwide", "Anywhere", "Global", "LATAM", "Latin America",
               "South America", "Remote", "Americas", "International"],
    "EUROPE": ["Worldwide", "Anywhere", "Global", "Europe", "European Union",
               "EU", "EMEA", "Remote", "International"],
    "ASIA":   ["Worldwide", "Anywhere", "Global", "Asia", "APAC",
               "Asia Pacific", "Remote", "International"],
    "USA":    ["Worldwide", "Anywhere", "Global", "United States",
               "North America", "Americas", "Remote", "International"],
    "GLOBAL": ["Worldwide", "Anywhere", "Global", "Remote", "International"],
}
_HIMALAYAS_EXCL_TERMS = {
    "LATAM":  ["United States", "United Kingdom", "Canada", "Australia",
               "Germany", "France", "India", "Brazil", "Poland", "Ukraine",
               "Israel", "Europe", "European Union", "Mexico", "Argentina",
               "Colombia", "China", "Japan"],
    "EUROPE": ["United States", "India", "Australia", "China", "Japan"],
    "ASIA":   ["United States", "Europe", "European Union", "Latin America"],
    "USA":    ["Europe", "European Union", "India", "Australia"],
    "GLOBAL": [],
}

_him_ok   = _HIMALAYAS_OK_TERMS.get(_CANDIDATE_REGION,   _HIMALAYAS_OK_TERMS["LATAM"])
_him_excl = _HIMALAYAS_EXCL_TERMS.get(_CANDIDATE_REGION, _HIMALAYAS_EXCL_TERMS["LATAM"])
_HIMALAYAS_LOC_OK      = re.compile(r"\b(" + "|".join(_him_ok)   + r")\b", re.I)
_HIMALAYAS_LOC_EXCLUDE = re.compile(r"\b(" + "|".join(_him_excl) + r")\b", re.I) if _him_excl else re.compile(r"(?!x)")

# Detecta país/ciudad en la URL del job (cuando worldwide=true falla)
_HIMALAYAS_URL_COUNTRY = re.compile(
    r"-(india|usa|canada|australia|brazil|united-kingdom|uk|gb|germany|"
    r"france|poland|ukraine|israel|china|japan|"
    r"chile|colombia|mexico|argentina|peru|"
    r"san-jose|new-york|london|berlin|sydney|toronto|"
    r"south-east-us|north-america)(?:-|$)",
    re.I,
)


def discover_himalayas() -> list[dict]:
    """Descubre ofertas en himalayas.app via API pública (sin auth).

    Usa el browse endpoint con worldwide=true para obtener todos los jobs
    sin restricción de país. Filtra Entry-level + Mid-level por seniority field.
    applicationLink = URL gratuita del job en Himalayas para el candidato.
    """
    seen: set[str] = set()
    jobs: list[dict] = []

    for offset in range(0, 220, 20):
        try:
            r = httpx.get(
                "https://himalayas.app/jobs/api",
                params={"limit": 20, "worldwide": "true", "offset": offset},
                headers=_HIMALAYAS_HEADERS,
                timeout=15,
            )
            if r.status_code != 200:
                break
            items = r.json().get("jobs", [])
            if not items:
                break
            for item in items:
                guid = item.get("guid", "")
                if not guid or guid in seen:
                    continue

                # Solo Entry-level y Mid-level (excluye Senior/Director/Manager)
                seniority = item.get("seniority") or []
                if seniority and not any(
                    s in ("Entry-level", "Mid-level") for s in seniority
                ):
                    continue

                # Excluir si la URL del job contiene país/ciudad específico
                apply_url = item.get("applicationLink", "")
                if _HIMALAYAS_URL_COUNTRY.search(apply_url):
                    continue

                seen.add(guid)
                jobs.append({
                    "title": item.get("title", ""),
                    "company": item.get("companyName", ""),
                    "url": apply_url,
                    "remote": True,
                    "source": "himalayas",
                    "description": item.get("description", ""),
                    "location_required": "",  # worldwide=true → sin restricción
                })
        except Exception:
            break

    return jobs


def filter_himalayas_location(jobs: list[dict]) -> list[dict]:
    """Filtra jobs de Himalayas por accesibilidad según CANDIDATE_REGION.

    - Sin locationRestrictions → pasa
    - Worldwide/Global o región del candidato → pasa
    - País/región incompatible → excluye
    - Ambiguo → pasa con location_warning
    """
    result = []
    for job in jobs:
        if job.get("source") != "himalayas":
            result.append(job)
            continue
        loc = job.get("location_required", "") or ""
        if not loc.strip():
            result.append(job)
            continue
        if _HIMALAYAS_LOC_OK.search(loc):
            result.append(job)
            continue
        if _HIMALAYAS_LOC_EXCLUDE.search(loc):
            continue
        job["location_warning"] = loc
        result.append(job)
    return result

# ---------------------------------------------------------------------------
# Wellfound (ex AngelList) — requiere sesión guardada con scripts/setup_wellfound_session.py
# ---------------------------------------------------------------------------

_WELLFOUND_SESSION = os.getenv(
    "WELLFOUND_SESSION_PATH",
    # src/boards/remote_global.py → boards → src → raíz del proyecto (3 niveles).
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".wellfound_session.json",
    ),
)

# Endpoint GraphQL de Wellfound (reverse-engineered)
_WELLFOUND_GQL = "https://wellfound.com/graphql?fallbackAOR=talent"

# ID de la operación persistida (puede cambiar si Wellfound actualiza su bundle)
_WELLFOUND_OP_ID = "tfe/b898ee628dd3385e1b8c467e464a0261ad66c478eda6e21e10566b0ca4ccf1e9"

# Keywords web3/crypto para excluir
_WELLFOUND_EXCLUDE_KW = ["web3", "crypto", "cryptocurrency", "blockchain", "nft", "defi"]


def discover_wellfound(max_pages: int = 5) -> list[dict]:
    """Descubre ofertas en Wellfound interceptando requests GraphQL del browser.

    Requiere sesión guardada en .wellfound_session.json
    (correr scripts/setup_wellfound_session.py una vez).

    DataDome bloquea headless → usa browser visible (headless=False).
    Intercepta la request JobSearchResultsX que el browser hace automáticamente.

    Estructura de respuesta:
      data.talent.jobSearchResults.startups.edges[].node.highlightedJobListings[]
    """
    if not os.path.exists(_WELLFOUND_SESSION):
        print("  [!] Sin sesión Wellfound. Corré: python scripts/setup_wellfound_session.py")
        return []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [!] playwright no instalado")
        return []

    jobs: list[dict] = []
    seen: set[str] = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=50,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                storage_state=_WELLFOUND_SESSION,
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )

            has_next = True
            page_num = 1

            while has_next and page_num <= max_pages:
                captured: list[dict] = []

                def _on_response(response, _cap=captured):
                    if "graphql" not in response.url or response.status != 200:
                        return
                    try:
                        op = response.request.post_data_json
                        if isinstance(op, dict) and op.get("operationName") == "JobSearchResultsX":
                            _cap.append(response.json())
                    except Exception:
                        pass

                page = context.new_page()
                page.on("response", _on_response)

                # Sin filtro de yearsExperience — nuestros filtros (filter_junior,
                # filter_entry_level) lo hacen downstream con mejor precisión.
                url = (
                    f"https://wellfound.com/jobs?remote=true&jobType=full_time"
                    f"&page={page_num}"
                )
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(6000)  # dar tiempo a que carguen los jobs
                page.close()

                if not captured:
                    break

                body = captured[-1]  # último response de JobSearchResultsX
                page_jobs, has_next = _wellfound_parse_response(body)

                for j in page_jobs:
                    if j["url"] not in seen:
                        seen.add(j["url"])
                        jobs.append(j)

                page_num += 1

            browser.close()

    except Exception as e:
        print(f"  [!] Wellfound error: {e}")

    return jobs


def _wellfound_parse_response(body: dict) -> tuple[list[dict], bool]:
    """Parsea el response JSON de JobSearchResultsX.

    Estructura:
      body.data.talent.jobSearchResults.startups.edges[].node
        .highlightedJobListings[].{title, slug, description, ...}
        .startup.{name, slug}
    """
    jobs: list[dict] = []
    has_next = False
    try:
        jsr = body["data"]["talent"]["jobSearchResults"]
        has_next = jsr.get("hasNextPage", False)
        edges = jsr.get("startups", {}).get("edges", [])

        for edge in edges:
            # El node ES la empresa directamente (no tiene .startup anidado)
            node         = edge.get("node", {})
            company      = node.get("name", "") or node.get("slug", "")
            company_slug = node.get("slug", "")
            listings     = node.get("highlightedJobListings", [])

            for item in listings:
                title = item.get("title", "")
                slug  = item.get("slug", "")
                desc  = item.get("description", "") or ""
                # URL canónica de Wellfound: /jobs/{company-slug}/{job-slug}
                apply_url = f"https://wellfound.com/jobs/{company_slug}/{slug}" if slug else ""
                if not title or not apply_url:
                    continue
                jobs.append({
                    "title":       title,
                    "company":     company,
                    "url":         apply_url,
                    "remote":      True,
                    "source":      "wellfound",
                    "description": desc,
                })
    except Exception:
        pass

    return jobs, has_next


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
# Hacker News "Who is hiring?" (API Algolia, sin anti-bot)
# ---------------------------------------------------------------------------

_HN_SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
_HN_ITEM = "https://hn.algolia.com/api/v1/items/{}"


def discover_hackernews() -> list[dict]:
    """Descubre ofertas del hilo mensual "Ask HN: Who is hiring?" (Algolia API).

    1) Busca el hilo whoishiring más reciente.
    2) Trae sus comentarios de primer nivel (cada uno = una oferta).
    3) Parseo heurístico de la primera línea (Company | Role | Location | ...),
       filtra por 'remote' + keyword tech del candidato.

    ponytail: parseo heurístico — el formato es libre, algunos campos saldrán
    imperfectos. Aceptado por diseño; el [!] de filter_global_remote + revisión
    manual cubren los ambiguos.
    """
    try:
        r = httpx.get(
            _HN_SEARCH,
            params={
                "tags": "story,author_whoishiring",
                "query": "who is hiring",
                "hitsPerPage": 5,
            },
            headers={**_HEADERS, "Accept": "application/json"},
            timeout=20,
        )
        r.raise_for_status()
        hits = r.json().get("hits", [])
    except Exception:
        return []

    thread_id = next(
        (h.get("objectID") for h in hits
         if "who is hiring" in (h.get("title") or "").lower()),
        None,
    )
    if not thread_id:
        return []

    try:
        r = httpx.get(
            _HN_ITEM.format(thread_id),
            headers={**_HEADERS, "Accept": "application/json"},
            timeout=30,
        )
        r.raise_for_status()
        children = r.json().get("children", [])
    except Exception:
        return []

    seen: set[str] = set()
    jobs: list[dict] = []

    for child in children:
        text = child.get("text")
        if not text:                      # comentario borrado
            continue
        plain = BeautifulSoup(text, "html.parser").get_text("\n").strip()
        if not plain:
            continue
        if "remote" not in plain.lower() or not TECH_FILTER.search(plain):
            continue

        first_line = plain.split("\n", 1)[0]
        parts = [p.strip() for p in first_line.split("|")]
        company = parts[0] if parts else ""
        role = parts[1] if len(parts) > 1 else first_line[:80]
        # Todo lo que sigue a la empresa → material para el geo-filtro
        location = " | ".join(parts[1:])[:60] if len(parts) > 1 else "Worldwide"

        a = BeautifulSoup(text, "html.parser").find("a", href=True)
        url = a["href"] if a else f"https://news.ycombinator.com/item?id={child.get('id')}"
        if url in seen:
            continue
        seen.add(url)

        jobs.append({
            "title":             role,
            "company":           company,
            "url":               url,
            "remote":            True,
            "source":            "hackernews",
            "description":       plain,
            "location_required": location,
        })

    return jobs
