#!/usr/bin/env python3
"""Guarda la sesión de GetOnBrd para auto-apply.

Flujo:
  1. Abre el browser en GetOnBrd
  2. Haces clic en "Sign in with email" y ponés tu email
  3. GetOnBrd te manda un link al correo
  4. Copiás ese link y lo pegás acá en la terminal
  5. El script lo abre en el mismo browser → sesión guardada

Solo necesitas hacer esto UNA vez (o cuando la sesión expire).
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

SESSION_PATH = os.getenv(
    "GETONBRD_SESSION_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gob_session.json"),
)

print("=" * 60)
print("SETUP — Sesión GetOnBrd")
print("=" * 60)
print()
print("Pasos:")
print("  1. Se abre el browser en GetOnBrd")
print("  2. Hacé clic en 'Sign in' → 'Professionals'")
print("  3. Hacé clic en 'Sign in with email' (icono sobre)")
print("  4. Ingresá tu email y mandá el magic link")
print("  5. Abrí tu correo, copiá el link (NO lo abras, solo copiálo)")
print("  6. Pegalo acá en la terminal cuando te lo pida")
print()
input("Presioná ENTER para abrir el browser...")

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
        viewport={"width": 1280, "height": 800},
        locale="es-EC",
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    )

    page = context.new_page()
    page.goto("https://www.getonbrd.com/webpros/login", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    print()
    print("Browser abierto.")
    print("→ Hacé clic en 'Sign in' → 'Professionals' → 'Sign in with email'")
    print("→ Ingresá tu email y enviá el magic link")
    print()
    print("Cuando tengas el email, copiá el link (clic derecho → copiar dirección)")
    print("NO lo abras en el browser normal — pegalo acá abajo.")
    print()

    magic_link = input("Pegá el magic link acá: ").strip()

    if not magic_link.startswith("http"):
        print("[!] Eso no parece una URL válida. Intentando de todas formas...")

    print(f"\nNavegando a: {magic_link[:80]}...")
    page.goto(magic_link, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    current_url = page.url
    print(f"URL resultante: {current_url}")

    if "/login" in current_url or "/auth" in current_url:
        print("[!] Parece que el link no funcionó o ya expiró.")
        print("    Los magic links de GetOnBrd expiran en pocos minutos.")
        print("    Volvé a correr el script y pegá el link rápido.")
        browser.close()
        sys.exit(1)

    # Verificar que estamos logueados navegando al dashboard
    page.goto("https://www.getonbrd.com/webpros/dashboard", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(2000)
    if "/login" in page.url:
        print("[!] No quedó logueado — intentá de nuevo.")
        browser.close()
        sys.exit(1)

    print(f"Logueado correctamente. Dashboard: {page.url}")
    context.storage_state(path=SESSION_PATH)
    print(f"\nSesión guardada en: {SESSION_PATH}")
    browser.close()

print("\nListo. Ahora corré:")
print("  .venv/bin/python3 run_discover.py --dry-run")
print()
