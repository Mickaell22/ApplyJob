"""
Apply ATS — Automatizacion de postulaciones en sistemas ATS (Workable, Teamtailor, Ashby, Workday, etc).

Usa Playwright para:
1. Navegar a la oferta
2. Aceptar cookies si aparece el banner
3. Hacer clic en "Apply"
4. Llenar campos del formulario
5. Subir CV
6. Pegar cover letter
7. Enviar
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Datos del candidato — se cargan desde .env (sin PII hardcodeada en el repo)
CANDIDATE = {
    "name": os.getenv("CANDIDATE_NAME", ""),
    "email": os.getenv("GMAIL_USER", ""),
    "phone": os.getenv("CANDIDATE_PHONE", ""),
    "location": os.getenv("CANDIDATE_LOCATION", ""),
    "city": os.getenv("CANDIDATE_CITY", ""),
    "country": os.getenv("CANDIDATE_COUNTRY", ""),
    "linkedin": os.getenv("CANDIDATE_LINKEDIN", ""),
    "github": os.getenv("CANDIDATE_GITHUB", ""),
    "cv_path": os.getenv("CV_PATH", "profile/cv.pdf"),
    "cv_path_en": os.getenv("CV_PATH_EN", "profile/cv_en.pdf"),
    "website": os.getenv("CANDIDATE_WEBSITE", ""),
}


def _get_browser():
    """Lanza un browser Chromium headless."""
    from playwright.sync_api import sync_playwright
    p = sync_playwright().start()
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    return browser, p


def dismiss_cookies(page):
    """Intenta aceptar/rechazar banners de cookies comunes."""
    patterns = [
        "Accept", "Accept all", "Accept All", "Aceptar", "Aceptar todas",
        "Aceptar cookies", "OK", "Continue", "Got it",
    ]
    for pattern in patterns:
        try:
            btn = page.query_selector(f"button:has-text('{pattern}')")
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                return True
        except Exception:
            continue
    return False


def detect_platform(url: str) -> str:
    """Detecta que plataforma ATS es."""
    url_lower = url.lower()
    if "workable.com" in url_lower:
        return "workable"
    elif "teamtailor.com" in url_lower:
        return "teamtailor"
    elif "ashbyhq.com" in url_lower or "jobs.ashby" in url_lower:
        return "ashby"
    elif "workday.com" in url_lower or "myworkdayjobs" in url_lower:
        return "workday"
    elif "greenhouse.io" in url_lower or "grnh.se" in url_lower:
        return "greenhouse"
    elif "lever.co" in url_lower:
        return "lever"
    elif "breezy.hr" in url_lower:
        return "breezy"
    elif "getonbrd.com" in url_lower:
        return "getonbrd"
    else:
        return "unknown"


def apply_workable(page, url: str, cover_letter: str, cv_abs_path: str) -> dict:
    """Postula en Workable."""
    print("  [Workable] Navegando...")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    dismiss_cookies(page)

    # Click "Apply for this job" or "Apply"
    apply_selectors = [
        'a[href*="/apply/"]',
        'button:has-text("Apply")',
        'button:has-text("APPLICATION")',
        'a:has-text("Apply for this job")',
    ]
    found = False
    for sel in apply_selectors:
        btn = page.query_selector(sel)
        if btn:
            try:
                btn.click(force=True)
                page.wait_for_timeout(3000)
                found = True
                print("  [Workable] Click en Apply")
                break
            except Exception as e:
                print(f"  [Workable] Error clicking {sel}: {e}")

    if not found:
        return {"error": "No se pudo encontrar boton Apply"}

    # Esperar a que cargue el formulario
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # Llenar campos del formulario
    fields_filled = []
    
    # Mapeo de campos Workable reales
    name_parts = CANDIDATE["name"].split(" ", 1)
    firstname = name_parts[0]
    lastname = name_parts[1] if len(name_parts) > 1 else ""

    workable_fields = {
        "firstname": firstname,
        "lastname": lastname,
        "email": CANDIDATE["email"],
        "phone": CANDIDATE["phone"],
        "address": CANDIDATE["location"],
        "city": CANDIDATE["city"],
        "country": CANDIDATE["country"],
        "linkedin": CANDIDATE["linkedin"],
    }

    filled = []
    for name, value in workable_fields.items():
        el = page.query_selector(f'[name="{name}"]')
        if el:
            try:
                el.fill(value)
                filled.append(name)
            except Exception:
                pass

    # Campos genericos si no existen los especificos
    if not filled:
        for sel, value in [
            ('input[type="email"]', CANDIDATE["email"]),
            ('input[type="tel"]', CANDIDATE["phone"]),
            ('input[name*="name"]', CANDIDATE["name"]),
        ]:
            el = page.query_selector(sel)
            if el:
                el.fill(value)
                filled.append(sel)

    fields_filled = filled

    print(f"  [Workable] Campos llenados: {fields_filled}")

    # Subir CV
    file_input = page.query_selector('input[type="file"]')
    if file_input:
        try:
            file_input.set_input_files(cv_abs_path)
            print(f"  [Workable] CV subido: {cv_abs_path}")
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"  [Workable] Error subiendo CV: {e}")

    # Pegar cover letter (textarea)
    textarea = page.query_selector("textarea")
    if textarea:
        textarea.fill(cover_letter)
        print("  [Workable] Cover letter pegada")
    else:
        # Buscar cualquier campo grande de texto
        for sel in ['div[contenteditable="true"]', '[data-placeholder*="Cover"]',
                    'div[class*="editor"]']:
            el = page.query_selector(sel)
            if el:
                el.fill(cover_letter)
                print(f"  [Workable] Cover letter pegada en {sel}")
                break

    page.wait_for_timeout(1000)
    return {"ok": True, "fields": fields_filled, "platform": "workable", "ready": True}


def apply_greenhouse(page, url: str, cover_letter: str, cv_abs_path: str) -> dict:
    """Postula en Greenhouse (boards.greenhouse.io)."""
    print("  [Greenhouse] Navegando...")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    dismiss_cookies(page)

    # Greenhouse a veces muestra la oferta y hay que clickear Apply,
    # otras veces carga directamente el formulario
    apply_selectors = [
        'a:has-text("Apply for this job")',
        'a:has-text("Apply now")',
        'button:has-text("Apply for this job")',
        'button:has-text("Apply now")',
        'button:has-text("Apply")',
        '#apply_button',
        '.apply-button',
    ]
    for sel in apply_selectors:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            try:
                btn.click()
                page.wait_for_timeout(2000)
                print(f"  [Greenhouse] Click en Apply ({sel})")
                break
            except Exception:
                pass

    # Esperar formulario — Greenhouse usa #application o carga directa
    try:
        page.wait_for_selector('input#first_name, input[name*="first_name"]', timeout=10000)
    except Exception:
        pass

    page.wait_for_timeout(1000)

    fields_filled = []
    name_parts = CANDIDATE["name"].split(" ", 1)
    firstname = name_parts[0]
    lastname = name_parts[1] if len(name_parts) > 1 else ""

    # Campos estándar de Greenhouse — IDs reales del formulario
    greenhouse_fields = [
        (['input#first_name', 'input[name*="first_name"]'], firstname),
        (['input#last_name', 'input[name*="last_name"]'], lastname),
        (['input#email', 'input[name*="[email]"]', 'input[type="email"]'], CANDIDATE["email"]),
        (['input#phone', 'input[name*="[phone]"]', 'input[type="tel"]'], CANDIDATE["phone"]),
    ]

    for selectors, value in greenhouse_fields:
        for sel in selectors:
            el = page.query_selector(sel)
            if el:
                try:
                    el.fill(value)
                    fields_filled.append(sel.split("#")[-1].split("[")[-1].rstrip("]"))
                    break
                except Exception:
                    pass

    # LinkedIn — Greenhouse suele tenerlo como pregunta custom con label
    for label in page.query_selector_all("label"):
        text = (label.inner_text() or "").lower()
        if "linkedin" in text:
            input_id = label.get_attribute("for")
            if input_id:
                el = page.query_selector(f"#{input_id}")
                if el:
                    try:
                        el.fill(CANDIDATE["linkedin"])
                        fields_filled.append("linkedin")
                    except Exception:
                        pass
            break

    print(f"  [Greenhouse] Campos llenados: {fields_filled}")

    # Subir CV — Greenhouse puede tener input#resume o un drop-zone
    resume_selectors = ['input#resume', 'input[name*="resume"]', 'input[type="file"]']
    for sel in resume_selectors:
        file_input = page.query_selector(sel)
        if file_input:
            try:
                file_input.set_input_files(cv_abs_path)
                print(f"  [Greenhouse] CV subido: {cv_abs_path}")
                page.wait_for_timeout(2000)
                break
            except Exception as e:
                print(f"  [Greenhouse] Error subiendo CV con {sel}: {e}")

    # Cover letter — textarea#cover_letter o área de texto libre
    cl_selectors = [
        'textarea#cover_letter',
        'textarea[name*="cover_letter"]',
        'textarea[placeholder*="cover"]',
        'textarea[placeholder*="Cover"]',
        'textarea',
    ]
    for sel in cl_selectors:
        textarea = page.query_selector(sel)
        if textarea and textarea.is_visible():
            try:
                textarea.fill(cover_letter)
                print(f"  [Greenhouse] Cover letter pegada ({sel})")
                break
            except Exception:
                pass

    page.wait_for_timeout(1000)
    return {"ok": True, "fields": fields_filled, "platform": "greenhouse", "ready": True}


def apply_teamtailor(page, url: str, cover_letter: str, cv_abs_path: str) -> dict:
    """Postula en Teamtailor."""
    print("  [Teamtailor] Navegando...")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    dismiss_cookies(page)

    # Buscar boton de postular
    apply_texts = ["Postular", "Apply", "Solicitar", "Enviar solicitud", "Apply for this job"]
    found = False
    for text in apply_texts:
        try:
            btn = page.query_selector(f"button:has-text('{text}')")
            if not btn:
                btn = page.query_selector(f"a:has-text('{text}')")
            if btn:
                btn.click(force=True)
                page.wait_for_timeout(3000)
                found = True
                print(f"  [Teamtailor] Click en '{text}'")
                break
        except Exception:
            continue

    if not found:
        return {"error": "No se pudo encontrar boton de postular"}

    # Esperar formulario
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # Llenar campos
    fields_filled = []

    # Full name
    for inp in page.query_selector_all("input:not([type=hidden])"):
        name = inp.get_attribute("name") or ""
        id_ = inp.get_attribute("id") or ""
        placeholder = inp.get_attribute("placeholder") or ""
        type_ = inp.get_attribute("type") or ""

        if type_ == "email" or "email" in (name + id_ + placeholder).lower():
            inp.fill(CANDIDATE["email"])
            fields_filled.append("email")
        elif "phone" in (name + id_ + placeholder).lower():
            inp.fill(CANDIDATE["phone"])
            fields_filled.append("phone")
        elif "name" in (name + id_ + placeholder).lower() and "first" not in (name + id_).lower():
            inp.fill(CANDIDATE["name"])
            fields_filled.append("name")
        elif "linkedin" in (name + id_ + placeholder).lower():
            inp.fill(CANDIDATE["linkedin"])
            fields_filled.append("linkedin")
        elif "city" in (name + id_ + placeholder).lower() or "location" in (name + id_ + placeholder).lower():
            inp.fill(CANDIDATE["location"])
            fields_filled.append("location")

    print(f"  [Teamtailor] Campos llenados: {fields_filled}")

    # Subir CV
    file_input = page.query_selector('input[type="file"]')
    if file_input:
        try:
            file_input.set_input_files(cv_abs_path)
            print(f"  [Teamtailor] CV subido")
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"  [Teamtailor] Error subiendo CV: {e}")

    return {"ok": True, "fields": fields_filled, "platform": "teamtailor", "ready": True}


_GOB_SESSION = os.getenv(
    "GETONBRD_SESSION_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".gob_session.json"),
)


def apply_getonbrd(context, url: str, cover_letter: str, cv_abs_path: str, dry_run: bool = False) -> dict:
    """Postula en GetOnBrd usando sesión guardada (.gob_session.json).

    GetOnBrd usa un formulario de 3 pasos:
      Step 1 (experience): cover letter (Trix editor) + nivel de inglés
      Step 2 (basic):      phone, linkedin, github, salary, reason_to_apply
      Step 3 (preview):    revisión antes del submit final

    Nota: GetOnBrd auto-crea un draft al navegar a /applications/new.
    Para drafts existentes (/edit) se salta directamente al step 2.
    Requiere haber corrido `setup_gob_session.py` al menos una vez.
    """
    if not os.path.exists(_GOB_SESSION):
        return {
            "error": (
                "Sesión de GetOnBrd no encontrada. "
                "Corre `python setup_gob_session.py` para guardarla."
            )
        }

    print("  [GetOnBrd] Navegando con sesión guardada...")
    page = context.new_page()
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    if "/login" in page.url or "/auth" in page.url:
        page.close()
        return {"error": "Sesión GetOnBrd expirada — corre setup_gob_session.py de nuevo"}

    # Aceptar cookies
    cookie_btn = page.query_selector("#accept_cookies button")
    if cookie_btn:
        cookie_btn.click()
        page.wait_for_timeout(800)

    fields_filled = []

    # ---- Step 1: Experience ------------------------------------------------
    trix = page.query_selector("trix-editor#trix-professional")
    if not trix:
        page.close()
        return {"error": "No se encontró el editor de cover letter (trix-professional)"}

    # Limpiar contenido previo y escribir la nueva carta
    trix.click()
    page.keyboard.press("Control+a")
    page.keyboard.type(cover_letter)
    page.wait_for_timeout(300)
    fields_filled.append("cover_letter")
    print("  [GetOnBrd] Step 1: cover letter llenada")

    # Nivel de inglés — solo en aplicaciones nuevas; required para que el server valide step 1
    # Verificar si el campo existe antes de intentar seleccionar
    eng_field = page.query_selector("#webpro_english_level")
    if eng_field:
        # Usar evaluate sin return statement (directamente la expresión)
        page.evaluate('document.querySelector(\'li[data-value="upper_intermediate"]\').click()')
        page.wait_for_timeout(300)
        eng_val = page.evaluate("document.querySelector('#webpro_english_level').value")
        if eng_val:
            fields_filled.append("english_level")

    # Enviar step 1 via fetch (bypass Stimulus controller que bloquea form.submit)
    # credentials: 'include' es necesario para enviar las cookies de sesión
    step1_result = page.evaluate("""
        async () => {
            const form = document.querySelector('#job-application-form');
            const data = new FormData(form);
            const body = new URLSearchParams([...data.entries()]).toString();
            try {
                const resp = await fetch(form.action, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept': 'text/html,application/xhtml+xml,*/*',
                    },
                    body: body,
                    redirect: 'follow'
                });
                return { status: resp.status, url: resp.url };
            } catch(e) {
                return { error: String(e) };
            }
        }
    """)

    if step1_result.get("error"):
        page.close()
        return {"error": f"Step 1 fetch error: {step1_result['error']}"}

    step2_url = step1_result.get("url", "")
    if not step2_url or "/edit" not in step2_url:
        page.close()
        return {"error": f"Step 1 no navegó a step 2 — respuesta: {step1_result}"}

    # Navegar la página al step 2 (el fetch no navega el browser)
    try:
        page.goto(step2_url, wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(1500)
    except Exception:
        page.wait_for_timeout(3000)

    if "/edit" not in page.url:
        page.close()
        return {"error": f"Step 2 no cargó — URL: {page.url}"}

    print(f"  [GetOnBrd] Step 2 cargado")

    # ---- Step 2: Basic info ------------------------------------------------
    for field, value in [
        ('input[name="webpro[phone]"]',    CANDIDATE["phone"]),
        ('input[name="webpro[linkedin]"]', CANDIDATE["linkedin"]),
        ('input[name="webpro[github]"]',   CANDIDATE["github"]),
    ]:
        el = page.query_selector(field)
        if el and el.is_visible():
            try:
                el.fill(value)
                fields_filled.append(field.split('"')[1])
            except Exception:
                pass

    # Reason to apply — primeras palabras de la cover letter (max 280 chars)
    reason_ta = page.query_selector('textarea[name="job_application[reason_to_apply]"]')
    if reason_ta and reason_ta.is_visible():
        short_reason = cover_letter[:280].rsplit(" ", 1)[0]
        reason_ta.fill(short_reason)
        fields_filled.append("reason_to_apply")

    print(f"  [GetOnBrd] Campos llenados: {fields_filled}")

    # dry_run: quedarse en step 2 sin enviar la postulación
    if dry_run:
        print("  [GetOnBrd] Dry-run: formulario listo en step 2, NO se envía")
        return {"ok": True, "fields": fields_filled, "platform": "getonbrd", "ready": True, "page": page}

    # Enviar step 2 via fetch → postulación real enviada
    step2_result = page.evaluate("""
        async () => {
            const form = document.querySelector('#job-application-form');
            const data = new FormData(form);
            const body = new URLSearchParams([...data.entries()]).toString();
            try {
                const resp = await fetch(form.action, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept': 'text/html,application/xhtml+xml,*/*',
                    },
                    body: body,
                    redirect: 'follow'
                });
                return { status: resp.status, url: resp.url };
            } catch(e) {
                return { error: String(e) };
            }
        }
    """)
    if step2_result.get("ok") is not False:
        print(f"  [GetOnBrd] Postulación enviada — {step2_result.get('url', '?').split('?')[-1]}")

    return {"ok": True, "fields": fields_filled, "platform": "getonbrd", "ready": True, "page": page}


def apply(page, url: str, cover_letter: str, cv_abs_path: str) -> dict:
    """Detecta plataforma y aplica."""
    platform = detect_platform(url)
    print(f"  Plataforma detectada: {platform}")

    if platform == "workable":
        return apply_workable(page, url, cover_letter, cv_abs_path)
    elif platform == "greenhouse":
        return apply_greenhouse(page, url, cover_letter, cv_abs_path)
    elif platform == "teamtailor":
        return apply_teamtailor(page, url, cover_letter, cv_abs_path)
    else:
        return {"error": f"Plataforma no soportada: {platform}"}


def apply_with_context(context, url: str, cover_letter: str, cv_abs_path: str, dry_run: bool = False) -> dict:
    """Versión de apply() que usa un browser context existente (para GetOnBrd con sesión)."""
    platform = detect_platform(url)
    print(f"  Plataforma: {platform}")
    if platform == "getonbrd":
        return apply_getonbrd(context, url, cover_letter, cv_abs_path, dry_run=dry_run)
    page = context.new_page()
    return apply(page, url, cover_letter, cv_abs_path)


def run(jobs_with_letters: list[dict], dry_run: bool = True, lang: str = "es") -> list[dict]:
    """Ejecuta postulaciones para una lista de (job, cover_letter)."""
    cv_key = "cv_path_en" if lang == "en" else "cv_path"
    cv_abs_path = str(Path(cv_path_resolve(cv_key)))

    if not os.path.exists(cv_abs_path):
        return [{"error": f"CV no encontrado en {cv_abs_path}"}]

    print(f"\n=== Apply ATS: {len(jobs_with_letters)} postulaciones ===")
    print(f"CV: {cv_abs_path}")
    print()

    browser, playwright = _get_browser()
    results = []

    try:
        for item in jobs_with_letters:
            job = item.get("job", {})
            letter = item.get("carta", "")
            url = job.get("url", "")

            print(f"Postulando: {job.get('title', '?')} en {job.get('company', '?')}")
            print(f"  URL: {url}")

            page = browser.new_page()

            try:
                result = apply(page, url, letter, cv_abs_path)
                result["job"] = job
                
                if result.get("ready"):
                    if dry_run:
                        print(f"  ⚠️ Dry run: formulario listo, NO se envio")
                        result["submitted"] = False
                    else:
                        # Intentar submit
                        submit_selectors = [
                            'button[type="submit"]:has-text("Submit")',
                            'button[type="submit"]:has-text("Submit application")',
                            'button[type="submit"]:has-text("Send")',
                            'button[type="submit"]:has-text("Apply")',
                            'button[type="submit"]:has-text("Enviar")',
                            'button[type="submit"]:has-text("Postular")',
                            'button[type="submit"]',
                        ]
                        submitted = False
                        for sel in submit_selectors:
                            btn = page.query_selector(sel)
                            if btn and btn.is_visible():
                                btn.click()
                                page.wait_for_timeout(3000)
                                submitted = True
                                result["submitted"] = True
                                print(f"  [Submit] Clickeado: {btn.inner_text()[:40]}")
                                break
                        if not submitted:
                            print(f"  [Submit] No se encontro boton")
                            result["submitted"] = False
                
                results.append(result)
                if result.get("ok"):
                    print(f"  ✅ Postulacion completada!\n")
                else:
                    print(f"  ❌ Fallo: {result.get('error', 'desconocido')}\n")
            except Exception as e:
                print(f"  ❌ Error: {e}\n")
                results.append({"error": str(e), "job": job})

            page.close()

    finally:
        browser.close()
        playwright.stop()

    # Resumen
    ok = sum(1 for r in results if r.get("ok"))
    print(f"=== Resumen: {ok}/{len(results)} exitosas ===")
    return results


def cv_path_resolve(key: str = "cv_path") -> str:
    """Resuelve la ruta absoluta del CV."""
    path = CANDIDATE[key]
    if not os.path.isabs(path):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.normpath(os.path.join(base, path))
    return path


if __name__ == "__main__":
    # Test rapido
    test_job = {
        "title": "Infrastructure Engineer",
        "company": "Platzi Colombia",
        "url": "https://apply.workable.com/platzi/j/40D4568480/",
    }
    test_letter = "Test cover letter..."
    run([{"job": test_job, "carta": test_letter}])
