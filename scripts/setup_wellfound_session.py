#!/usr/bin/env python3
"""Guarda la sesión de Wellfound para discover_wellfound().

Flujo:
  1. Abre el browser en wellfound.com/login
  2. Llena email + password desde .env (WELLFOUND_EMAIL / WELLFOUND_PASSWORD)
  3. Si hay captcha/verificación, la resolvés vos manualmente
  4. Sesión guardada en .wellfound_session.json

Solo necesitás hacer esto UNA vez (o cuando la sesión expire).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

SESSION_PATH = os.getenv(
    "WELLFOUND_SESSION_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".wellfound_session.json"),
)

EMAIL    = os.getenv("WELLFOUND_EMAIL", "")
PASSWORD = os.getenv("WELLFOUND_PASSWORD", "")

if not EMAIL or not PASSWORD:
    print("[!] Faltan WELLFOUND_EMAIL y/o WELLFOUND_PASSWORD en el .env")
    print("    Agregá estas líneas al .env:")
    print("    WELLFOUND_EMAIL=tu@email.com")
    print("    WELLFOUND_PASSWORD=tu_contraseña")
    sys.exit(1)

print("=" * 60)
print("SETUP — Sesión Wellfound")
print("=" * 60)
print()
print(f"Email: {EMAIL}")
print()
print("Se abrirá el browser para hacer login.")
print("Si Wellfound pide verificación o captcha, resuélvelo vos.")
print()
input("Presioná ENTER para abrir el browser...")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        slow_mo=80,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
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
    print("\nNavegando a wellfound.com/login...")
    page.goto("https://wellfound.com/login", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    # Llenar email
    email_sel = 'input[name="email"], input[type="email"], input[placeholder*="email" i]'
    try:
        page.wait_for_selector(email_sel, timeout=8000)
        page.fill(email_sel, EMAIL)
        print(f"  Email ingresado: {EMAIL}")
    except Exception:
        print("  [!] No encontré el campo email — completalo vos en el browser")

    # Llenar password
    pass_sel = 'input[name="password"], input[type="password"]'
    try:
        page.wait_for_selector(pass_sel, timeout=5000)
        page.fill(pass_sel, PASSWORD)
        print("  Password ingresado.")
    except Exception:
        print("  [!] No encontré el campo password — completalo vos en el browser")

    # Submit
    try:
        submit_sel = 'button[type="submit"], button:has-text("Log In"), button:has-text("Sign In")'
        btn = page.query_selector(submit_sel)
        if btn:
            btn.click()
            print("  Enviando formulario...")
        else:
            print("  [!] No encontré el botón submit — hacé click vos")
    except Exception:
        print("  [!] Error al hacer submit — hacé click vos")

    print()
    print("Esperando login completado...")
    print("(Si hay captcha o verificación, resuélvelo en el browser)")
    print()

    # Esperar hasta que ya no estemos en /login
    try:
        page.wait_for_url(
            lambda url: "/login" not in url and "/users/sign_in" not in url,
            timeout=60000,
        )
        print(f"Login OK. URL: {page.url}")
    except Exception:
        print(f"[!] Timeout esperando redirect. URL actual: {page.url}")
        print("    Si ya estás logueado, presioná ENTER para continuar.")
        input()

    # Verificar navegando a /jobs
    print("Verificando sesión en /jobs...")
    page.goto("https://wellfound.com/jobs", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(2000)

    if "/login" in page.url or "/users/sign_in" in page.url:
        print("[!] No quedó logueado — intentá de nuevo.")
        browser.close()
        sys.exit(1)

    print(f"Sesión activa. URL: {page.url}")
    context.storage_state(path=SESSION_PATH)
    print(f"\nSesión guardada en: {SESSION_PATH}")
    browser.close()

print()
print("Listo. Ahora podés correr:")
print("  .venv/bin/python3 run_discover.py wellfound --no-apply")
print()
