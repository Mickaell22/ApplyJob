"""Extrae informacion de ofertas laborales desde URLs.

Estrategia:
1. httpx con User-Agent de navegador (rapido, para sitios simples)
2. Playwright headless (para sitios con JavaScript/React/Cloudflare)
3. Si ambos fallan, devuelve el error
"""

import re
import httpx
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-EC,es;q=0.9,en;q=0.8",
}

# Rotacion de User-Agents
_USER_AGENTS = [
    _HEADERS["User-Agent"],
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def fetch_job(url: str) -> dict:
    """Abre una URL de oferta y extrae titulo, empresa, descripcion, requisitos."""
    # Intento 1: httpx rapido
    result = _try_httpx(url)
    if "error" not in result:
        return result

    # Intento 2: Playwright headless (para JS/React/Cloudflare)
    result = _try_playwright(url)
    if "error" not in result:
        return result

    # Si ambos fallan, devolver el error del primer intento
    return result


def _try_httpx(url: str) -> dict:
    """Intenta extraer via httpx con headers de navegador.
    Sigue redirects y devuelve la URL final."""
    for ua in _USER_AGENTS:
        try:
            headers = dict(_HEADERS)
            headers["User-Agent"] = ua
            resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=20)
            resp.raise_for_status()
            return _parse_html(resp.text, resp.url)
        except Exception:
            continue
    return {"url": url, "error": "httpx fallo para todas las variantes"}


def _try_playwright(url: str) -> dict:
    """Intenta extraer via Playwright headless (para JS/React).
    Primero resuelve la URL final (redirects) y va directo."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"url": url, "error": "playwright no instalado"}

    # Resolver short URL primero con httpx
    final_url = url
    try:
        resp = httpx.head(url, follow_redirects=True, timeout=10)
        final_url = str(resp.url)
    except Exception:
        pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = browser.new_page(
                user_agent=_USER_AGENTS[0],
                locale="es-EC",
                extra_http_headers={"Accept-Language": "es-EC,es;q=0.9"},
            )
            page.goto(final_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
            return _parse_html(html, final_url)
    except Exception as e:
        return {"url": final_url, "error": f"playwright: {str(e)[:80]}"}


def _parse_html(html: str, url: str) -> dict:
    """Parsea el HTML y extrae titulo, empresa, descripcion."""
    soup = BeautifulSoup(html, "html.parser")

    # Solo eliminar scripts y estilos (no nav/footer - pueden tener contenido util)
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Texto completo del body
    body = soup.find("body") or soup
    text = body.get_text(separator=" ", strip=True)

    # Intentar encontrar contenido principal
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_=re.compile(r"job-description|description__content|posting-body|careers-posting|content-wrapper|main-content"))
        or soup.find("section", class_=re.compile(r"job-description|description__content|posting-body"))
    )
    content_text = (main.get_text(separator=" ", strip=True) if main else text)[:6000]

    return {
        "url": url,
        "title": _extract_title(soup, text),
        "company": _extract_company(soup, text),
        "description": content_text if content_text else text[:3000],
    }


def fetch_all(urls: list[str]) -> list[dict]:
    """Procesa varias URLs."""
    return [fetch_job(u) for u in urls if u]


def _extract_title(soup: BeautifulSoup, text: str) -> str:
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    titles = re.findall(
        r"(?:Backend|Frontend|Fullstack|iOS|Android|DevOps|QA|Data|Developer|Engineer|Software)"
        r".{0,60}(?:Engineer|Developer|Intern|Practicas)",
        text, re.I,
    )
    return titles[0] if titles else "Sin titulo"


def _extract_company(soup: BeautifulSoup, text: str) -> str:
    meta = soup.find("meta", attrs={"name": "application-name"})
    if meta:
        return meta.get("content", "")
    for selectors in [
        r"en\s+([A-Z][a-záéíóú]+(?:\s[A-Z][a-záéíóú]+)*)",
        r"([A-Z][a-záéíóú]+)\s+busca",
        r"([A-Z][a-záéíóú]+)\s+necesita",
    ]:
        match = re.search(selectors, text[:500], re.I)
        if match:
            return match.group(1)
    return "Desconocida"
