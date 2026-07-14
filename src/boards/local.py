"""Boards del canal LOCAL (pais del candidato): Computrabajo y Multitrabajos."""

import json
import os
import re
import time
from urllib.parse import urlencode
import httpx
from bs4 import BeautifulSoup
from ._common import *  # noqa: F401,F403


# ---------------------------------------------------------------------------
# Computrabajo (canal local) — server-rendered, httpx + BS4
# ---------------------------------------------------------------------------

# Subdominio por pais (ec, mx, co, pe, ...) — configurable via .env
_COMPUTRABAJO_DOMAIN = os.getenv("COMPUTRABAJO_DOMAIN", "ec.computrabajo.com")
_CT_KEYWORDS = ["desarrollador", "programador"]


def discover_computrabajo(max_pages: int = 2) -> list[dict]:
    """Canal LOCAL: ofertas en Computrabajo del pais (COMPUTRABAJO_DOMAIN).

    HTML server-rendered: tarjetas <article class="box_offer">, titulo+URL en
    <a class="js-o-link">, empresa en <a offer-grid-article-company-url>,
    ubicacion en el <p class="fs16"> sin links. Paginacion con ?p=N.
    La descripcion no viene en el listado -> la scrapea el pipeline.
    """
    seen: set[str] = set()
    jobs: list[dict] = []

    for kw in _CT_KEYWORDS:
        for page in range(1, max_pages + 1):
            try:
                r = httpx.get(
                    f"https://{_COMPUTRABAJO_DOMAIN}/trabajo-de-{kw}",
                    params={"p": page} if page > 1 else None,
                    headers={**_HEADERS, "Accept-Language": "es-EC,es;q=0.9"},
                    follow_redirects=True,
                    timeout=20,
                )
                if r.status_code != 200:
                    break
            except Exception:
                break

            soup = BeautifulSoup(r.text, "html.parser")
            arts = soup.find_all("article", class_=re.compile(r"box_offer"))
            if not arts:
                break

            for art in arts:
                a = art.find("a", class_=re.compile(r"js-o-link"))
                if not a:
                    continue
                href = (a.get("href") or "").split("#")[0]
                full = href if href.startswith("http") else f"https://{_COMPUTRABAJO_DOMAIN}{href}"
                if not href or full in seen:
                    continue
                seen.add(full)

                comp_el = art.find("a", attrs={"offer-grid-article-company-url": True})
                loc = ""
                for pel in art.find_all("p", class_=re.compile(r"fs16")):
                    if not pel.find("a"):
                        loc = pel.get_text(" ", strip=True)
                        break

                jobs.append({
                    "title":             a.get_text(strip=True),
                    "company":           comp_el.get_text(strip=True) if comp_el else "",
                    "url":               full,
                    "remote":            None,  # se detecta al scrapear la descripcion
                    "source":            "computrabajo",
                    "description":       "",
                    "location_required": loc,
                    "canal":             "local",
                })

            if len(arts) < 20:  # ultima pagina
                break
            time.sleep(1)

    return jobs


# ---------------------------------------------------------------------------
# Multitrabajos (canal local, Ecuador — red Bumeran) — SPA via Playwright
# ---------------------------------------------------------------------------

_MT_BASE = "https://www.multitrabajos.com"
_MT_KEYWORDS = ["desarrollador", "programador"]
_MT_SKIP_TEXT = re.compile(
    r"^(Nuevo|Publicado|Actualizado|Postulaci[óo]n r[áa]pida|Great Place to Work)", re.I
)
_MT_MODALIDAD = re.compile(r"^(Presencial|H[íi]brido|Remoto)$", re.I)
_MT_LOC = re.compile(r"^[^,|]{3,40},\s*[^,|]{3,40}$")


def discover_multitrabajos(max_pages: int = 2) -> list[dict]:
    """Canal LOCAL: Multitrabajos.com (board #1 de Ecuador, red Bumeran).

    La API JSON esta tras Cloudflare (403 directo) y el HTML es una SPA React
    -> se renderiza cada pagina con Playwright headless y se parsea el DOM.

    ponytail: parseo heuristico de stripped_strings por tarjeta (tras saltar
    "Nuevo"/"Publicado...": titulo, empresa, ubicacion 'Ciudad, Provincia',
    modalidad, descripcion si es larga). Techo: si Bumeran cambia el markup se
    rompe; upgrade = interceptar el XHR de la SPA con page.on("response").
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [!] playwright no instalado — multitrabajos omitido")
        return []

    seen: set[str] = set()
    jobs: list[dict] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(user_agent=_HEADERS["User-Agent"])

            for kw in _MT_KEYWORDS:
                for n in range(1, max_pages + 1):
                    url = f"{_MT_BASE}/empleos-busqueda-{kw}.html"
                    if n > 1:
                        url += f"?page={n}"
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(6000)  # SPA: esperar el fetch de avisos
                        soup = BeautifulSoup(page.content(), "html.parser")
                    except Exception:
                        break

                    found = 0
                    for a in soup.find_all("a", href=re.compile(r"/empleos/.+\.html$")):
                        href = a.get("href", "")
                        full = href if href.startswith("http") else _MT_BASE + href
                        if full in seen:
                            continue
                        texts = [t for t in a.stripped_strings if not _MT_SKIP_TEXT.match(t)]
                        if len(texts) < 2:
                            continue
                        title, company = texts[0], texts[1]
                        rest = texts[2:]
                        loc = next((t for t in rest if _MT_LOC.match(t)), "")
                        modalidad = next((t for t in rest if _MT_MODALIDAD.match(t)), "")
                        desc = max((t for t in rest if len(t) > 120), key=len, default="")

                        seen.add(full)
                        jobs.append({
                            "title":             title,
                            "company":           company,
                            "url":               full,
                            "remote":            True if modalidad.lower() == "remoto" else None,
                            "source":            "multitrabajos",
                            "description":       desc,
                            "location_required": loc,
                            "canal":             "local",
                        })
                        found += 1

                    if found == 0:  # pagina sin avisos nuevos -> fin
                        break

            browser.close()
    except Exception as e:
        print(f"  [!] Multitrabajos error: {e}")

    return jobs
