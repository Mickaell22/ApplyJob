#!/usr/bin/env python3
"""Guarda la sesion LOGUEADA de LinkedIn para el board `linkedin-auth`.

Logueado, LinkedIn muestra muchas mas ofertas que el endpoint guest (y sin el
rate-limit 429 agresivo). Este script abre un browser real para que TE loguees
a mano (usuario + contrasena + 2FA/captcha si aparecen) y guarda la cookie de
sesion en un storage_state que el scraper reusa despues.

Flujo:
  1. Se abre el browser en la pagina de login de LinkedIn.
  2. Te logueas normalmente (resolve 2FA/captcha si LinkedIn los pide).
  3. Cuando veas tu feed, volves a esta terminal y presionas ENTER.
  4. La sesion queda guardada en LINKEDIN_SESSION_PATH.

Solo hay que hacerlo UNA vez (la cookie li_at dura ~1 ano) o cuando caduque.

OJO: scrapear LinkedIn logueado va contra sus Terminos y hay riesgo (bajo, pero
real) de restriccion de la cuenta. Es tu cuenta personal: el scraper va lento y
con poco volumen a proposito. Usalo con criterio.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

SESSION_PATH = os.getenv(
    "LINKEDIN_SESSION_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".linkedin_session.json"),
)

print("=" * 60)
print("SETUP — Sesion LinkedIn (para board linkedin-auth)")
print("=" * 60)
print()
print("Pasos:")
print("  1. Se abre el browser en el login de LinkedIn.")
print("  2. Logueate normalmente (email + password + 2FA/captcha si aparece).")
print("  3. Cuando veas tu feed/inicio, volve aca y presiona ENTER.")
print("  4. La sesion se guarda y ya podes correr:")
print("        .venv/bin/python3 cli/run_discover.py linkedin-auth --no-apply")
print()
input("Presiona ENTER para abrir el browser...")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        slow_mo=50,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        locale="en-US",
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    )

    page = context.new_page()
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

    print()
    print("Browser abierto en LinkedIn.")
    print("→ Logueate a mano. Resolve 2FA/captcha si LinkedIn los pide.")
    print("→ Esperá a ver tu feed (URL con /feed).")
    print()
    input("Cuando estes logueado y viendo el feed, presiona ENTER aca...")

    # Verificar que quedo logueado: el feed real no redirige a /login ni /checkpoint
    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)
    if any(x in page.url for x in ("/login", "/checkpoint", "/authwall")):
        print(f"[!] No parece logueado (URL: {page.url}).")
        print("    Volve a correr el script y completa el login antes de dar ENTER.")
        browser.close()
        sys.exit(1)

    context.storage_state(path=SESSION_PATH)
    print(f"\nLogueado. Sesion guardada en: {SESSION_PATH}")
    browser.close()

print("\nListo. Ahora corre:")
print("  .venv/bin/python3 cli/run_discover.py linkedin-auth --no-apply")
print()
