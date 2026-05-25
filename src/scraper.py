"""Extrae informacion de ofertas laborales desde URLs."""

import re
import httpx
from bs4 import BeautifulSoup


def fetch_job(url: str) -> dict | None:
    """Abre una URL de oferta y extrae titulo, empresa, descripcion, requisitos."""
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        return {"url": url, "error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    return {
        "url": url,
        "title": _extract_title(soup, text),
        "company": _extract_company(soup, text),
        "description": text[:3000],
    }


def fetch_all(urls: list[str]) -> list[dict]:
    """Procesa varias URLs."""
    return [fetch_job(u) for u in urls if u]


def _extract_title(soup: BeautifulSoup, text: str) -> str:
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    titles = re.findall(r"(?:Backend|Frontend|Fullstack|iOS|Android|DevOps|QA|Data).{0,60}(?:Engineer|Developer|Intern|Practicas)", text, re.I)
    return titles[0] if titles else "Sin titulo"


def _extract_company(soup: BeautifulSoup, text: str) -> str:
    meta = soup.find("meta", attrs={"name": "application-name"})
    if meta:
        return meta.get("content", "")
    match = re.search(r"(?:en|@)\s*([A-Z][a-záéíóú]+(?:\s[A-Z][a-záéíóú]+)*)", text[:500])
    return match.group(1) if match else "Desconocida"
