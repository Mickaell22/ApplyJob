"""Resolucion de URLs de postulacion (GetOnBrd -> ATS externo)."""

import json
import os
import re
import time
from urllib.parse import urlencode
import httpx
from bs4 import BeautifulSoup
from ._common import *  # noqa: F401,F403


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
