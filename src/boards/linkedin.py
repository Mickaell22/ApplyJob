"""LinkedIn: guest (sin login), canal local del pais, y autenticado (sesion guardada)."""

import json
import os
import re
import time
from urllib.parse import urlencode
import httpx
from bs4 import BeautifulSoup
from ._common import *  # noqa: F401,F403


# ---------------------------------------------------------------------------
# LinkedIn (jobs-guest endpoint público, SIN login)
# ---------------------------------------------------------------------------

_LINKEDIN_GUEST_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)

# Headers realistas obligatorios — sin Accept-Language en-US → bloqueo
_LINKEDIN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_LINKEDIN_KEYWORDS = [
    "python developer", "full stack developer", "backend developer",
    "react developer", "node.js developer", "django",
]


def discover_linkedin(
    keywords: list[str] | None = None,
    remote_only: bool = True,
    max_pages: int = 3,
    location: str = "Worldwide",
) -> list[dict]:
    """Descubre ofertas en LinkedIn via el endpoint guest (sin auth).

    Itera keywords x páginas, parsea las tarjetas HTML y normaliza al schema.
    Filtros nativos: f_WT=2 (remote), f_E=1,2 (Internship+Entry), f_TPR=última
    semana. La descripción no viene en el listado → queda vacía y el pipeline
    la scrapea después con fetch_job().

    ponytail: rate-limit agresivo de LinkedIn (429). Techo conocido: vamos
    lento (sleep 4s/página, max_pages bajo) y cortamos la keyword al primer
    429. Upgrade si hiciera falta: proxy rotativo / backoff exponencial.
    """
    keywords = keywords or _LINKEDIN_KEYWORDS
    seen: set[str] = set()
    jobs: list[dict] = []

    for kw in keywords:
        for page in range(max_pages):
            params = {
                "keywords": kw,
                "location": location,
                "f_E": "1,2",            # 1=Internship, 2=Entry level
                "f_TPR": "r604800",      # publicado en la última semana
                "start": page * 10,
            }
            if remote_only:
                params["f_WT"] = "2"     # 2=Remote

            try:
                r = httpx.get(
                    _LINKEDIN_GUEST_URL,
                    params=params,
                    headers=_LINKEDIN_HEADERS,
                    timeout=20,
                )
            except Exception:
                break
            if r.status_code != 200:     # 429 u otro → abandonar esta keyword
                break

            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"base-(search-)?card"))
            if not cards:
                break

            for card in cards:
                title_el = card.find(class_=re.compile(r"base-search-card__title"))
                # Solo el link de la oferta (/jobs/view/...) — evita el link del
                # logo de empresa (/company/...) que duplicaría cada tarjeta.
                link_el = card.find("a", href=re.compile(r"/jobs/view/"))
                if not title_el or not link_el:
                    continue
                url = (link_el.get("href") or "").split("?")[0].strip()
                if not url or url in seen:
                    continue
                seen.add(url)

                company_el = card.find(class_=re.compile(r"base-search-card__subtitle"))
                loc_el = card.find(class_=re.compile(r"job-search-card__location"))
                jobs.append({
                    "title":             title_el.get_text(strip=True),
                    "company":           company_el.get_text(strip=True) if company_el else "",
                    "url":               url,
                    "remote":            True if remote_only else None,
                    "source":            "linkedin",
                    "description":       "",
                    "location_required": loc_el.get_text(strip=True) if loc_el else "",
                })

            time.sleep(4)  # ponytail: ir lento para no comerse un 429

    return jobs


def discover_linkedin_local(max_pages: int = 2) -> list[dict]:
    """Canal LOCAL: ofertas en el pais del candidato (presencial/hibrido/remoto-pais).

    Reusa discover_linkedin() cambiando location al pais del candidato
    (CANDIDATE_COUNTRY del .env) y quitando el filtro remoto f_WT=2. Mantiene
    f_E=1,2 (Internship+Entry). Los jobs salen con canal="local" para que el
    pipeline NO les aplique el geo-filtro remoto-global.

    ponytail: se busca por pais entero, no por ciudad — capta remoto-dentro-del-
    pais (valioso) a costa de ruido presencial de otras ciudades; el campo
    location queda visible para descartarlo a mano.
    """
    country = os.getenv("CANDIDATE_COUNTRY", "").strip()
    location = country or os.getenv("CANDIDATE_LOCATION", "").strip()
    if not location:
        print("  [!] Sin CANDIDATE_COUNTRY/CANDIDATE_LOCATION en .env — canal local omitido")
        return []

    jobs = discover_linkedin(remote_only=False, max_pages=max_pages, location=location)
    for j in jobs:
        j["source"] = "linkedin-local"
        j["canal"] = "local"
    return jobs


# ---------------------------------------------------------------------------
# LinkedIn AUTENTICADO — sesion guardada (setup_linkedin_session.py) + Playwright
# ---------------------------------------------------------------------------

_LINKEDIN_SESSION_PATH = os.getenv(
    "LINKEDIN_SESSION_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".linkedin_session.json"),
)
_LINKEDIN_AUTH_SEARCH = "https://www.linkedin.com/jobs/search/"


def discover_linkedin_auth(
    keywords: list[str] | None = None,
    remote_only: bool = True,
    max_pages: int = 2,
    location: str = "Worldwide",
) -> list[dict]:
    """Descubre ofertas en LinkedIn con la sesion LOGUEADA del candidato.

    A diferencia de discover_linkedin() (endpoint guest, muy limitado y con
    rate-limit 429 agresivo), esto reusa la cookie de sesion guardada por
    setup_linkedin_session.py: LinkedIn logueado devuelve mas resultados y sin
    el bloqueo del guest. Se renderiza con Playwright (SPA) y se parsea el DOM.

    Requiere correr ANTES `setup_linkedin_session.py` una vez (abre el browser,
    te logueas a mano —incluido 2FA/captcha— y se guarda la sesion). Si no hay
    sesion guardada, devuelve [] con un aviso.

    ponytail: parseo heuristico del DOM logueado (clases job-card-container).
    Techo: LinkedIn cambia/ofusca el markup seguido y puede pedir checkpoint;
    upgrade = interceptar el XHR voyager (page.on("response")) en vez del DOM.
    """
    if not os.path.exists(_LINKEDIN_SESSION_PATH):
        print("  [!] Sin sesion LinkedIn — corre primero: python3 setup_linkedin_session.py")
        return []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [!] playwright no instalado — linkedin-auth omitido")
        return []

    keywords = keywords or _LINKEDIN_KEYWORDS
    headless = os.getenv("LINKEDIN_HEADLESS", "1").strip().lower() not in ("0", "false", "no")
    seen: set[str] = set()
    jobs: list[dict] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                storage_state=_LINKEDIN_SESSION_PATH,
                user_agent=_HEADERS["User-Agent"],
                locale="en-US",
                viewport={"width": 1280, "height": 900},
            )
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )
            page = context.new_page()

            for kw in keywords:
                for n in range(max_pages):
                    params = {
                        "keywords": kw,
                        "location": location,
                        "f_E": "1,2",        # 1=Internship, 2=Entry level
                        "f_TPR": "r604800",  # ultima semana
                        "start": n * 25,
                    }
                    if remote_only:
                        params["f_WT"] = "2"
                    url = _LINKEDIN_AUTH_SEARCH + "?" + urlencode(params)
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        # Si la sesion caduco, LinkedIn redirige a login/checkpoint
                        if any(x in page.url for x in ("/login", "/checkpoint", "/authwall")):
                            print("  [!] Sesion LinkedIn caducada — recorre setup_linkedin_session.py")
                            browser.close()
                            return jobs
                        page.wait_for_timeout(3500)
                        # scroll para forzar el lazy-load de la lista
                        for _ in range(3):
                            page.mouse.wheel(0, 4000)
                            page.wait_for_timeout(1200)
                        soup = BeautifulSoup(page.content(), "html.parser")
                    except Exception:
                        break

                    found = 0
                    for a in soup.find_all("a", href=re.compile(r"/jobs/view/\d+")):
                        m = re.search(r"/jobs/view/(\d+)", a.get("href", ""))
                        if not m:
                            continue
                        job_id = m.group(1)
                        if job_id in seen:
                            continue
                        title = (a.get("aria-label") or a.get_text(" ", strip=True)).strip()
                        if not title:
                            continue
                        seen.add(job_id)

                        # Subir al contenedor de la tarjeta para empresa/ubicacion
                        card = a.find_parent(class_=re.compile(r"job-card-container|scaffold-layout__list-item")) or a.parent
                        company = loc = ""
                        sub = card.find(class_=re.compile(r"artdeco-entity-lockup__subtitle|job-card-container__primary-description"))
                        if sub:
                            company = sub.get_text(" ", strip=True)
                        met = card.find(class_=re.compile(r"artdeco-entity-lockup__caption|job-card-container__metadata"))
                        if met:
                            loc = met.get_text(" ", strip=True)

                        jobs.append({
                            "title":             title,
                            "company":           company,
                            "url":               f"https://www.linkedin.com/jobs/view/{job_id}/",
                            "remote":            True if remote_only else None,
                            "source":            "linkedin-auth",
                            "description":       "",
                            "location_required": loc,
                        })
                        found += 1

                    if found == 0:  # pagina sin resultados nuevos -> fin de esta keyword
                        break
                    time.sleep(2)  # ponytail: cortesia entre paginas para no gatillar checkpoint

            browser.close()
    except Exception as e:
        print(f"  [!] LinkedIn auth error: {e}")

    return jobs
