#!/usr/bin/env python3
"""Descubre ofertas nuevas desde tableros, matchea, genera cartas.

Boards:
  - GetOnBrd        (getonbrd.com)          — API JSON, LATAM remoto
  - Himalayas       (himalayas.app)         — API JSON, global, filtro Entry-level nativo
  - We Work Remotely(weworkremotely.com)    — RSS, global, jobs de calidad
  - 4 Day Week      (4dayweek.io)           — API JSON, remoto entry/mid
  - Remote First Jobs(remotefirstjobs.com)  — API JSON, entry-level, global
  - Working Nomads  (workingnomads.com)     — API JSON, global, 100% remoto
  - Remotive        (remotive.com)          — API JSON (limitada a ~28 jobs)
  - LinkedIn LOCAL  (linkedin-local)        — canal local: jobs en el pais del
    candidato (CANDIDATE_COUNTRY), presencial/hibrido/remoto-pais, canal="local"

Filtros aplicados automaticamente:
  1. Solo keywords técnicas (python, backend, fullstack, react, etc.)
  2. Sin senior/lead/architect en el título
  3. Sin "3+ años de experiencia" en la descripción
  4. Sin restricción de país que excluya Ecuador (solo canal remoto;
     el canal local no pasa por el geo-filtro)

Uso:
  python run_discover.py                # todos los boards + genera cartas
  python run_discover.py --no-apply     # igual (modo default, sin auto-apply)
  python run_discover.py getonbrd       # solo GetOnBrd
  python run_discover.py himalayas      # solo Himalayas
  python run_discover.py weworkremotely # solo We Work Remotely
  python run_discover.py 4dayweek       # solo 4 Day Week
  python run_discover.py remotefirstjobs # solo Remote First Jobs
  python run_discover.py workingnomads  # solo Working Nomads
  python run_discover.py remotive       # solo Remotive
  python run_discover.py linkedin-local # solo LinkedIn local (pais del candidato)
  python run_discover.py computrabajo   # solo Computrabajo (COMPUTRABAJO_DOMAIN)
  python run_discover.py multitrabajos  # solo Multitrabajos (Ecuador, Playwright)
  python run_discover.py local          # los 3 boards del canal local juntos
  python run_discover.py --verify       # descartar ofertas expiradas (request extra c/u)
  python run_discover.py --no-remote    # incluir presenciales
"""

import re
import sys
import os
import json
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# OJO: cover (DeepSeek/anthropic) se importa lazy mas abajo, solo con --with-cover.
# Asi el modo listado (default, 0 API) corre sin la dependencia anthropic.
from src import profile, matcher, apply_ats
from src import boards
from src import applied
from src.scraper import fetch_job

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "cartas")
os.makedirs(OUT_DIR, exist_ok=True)

# URLs ya postuladas (carta generada / envio real) y ya listadas en corridas
# previas — se saltan para no duplicar. Logica compartida en src/applied.py.
applied_urls = applied.load_applied()
seen_urls    = applied.load_seen()

# Argumentos
args = sys.argv[1:]
only_board  = next((a for a in args if a in (
    "getonbrd", "himalayas", "weworkremotely", "4dayweek",
    "remotefirstjobs", "workingnomads", "remotive", "glovo", "wellfound",
    "linkedin", "linkedin-auth", "hackernews", "linkedin-local", "computrabajo",
    "multitrabajos", "local",
)), None)
remote_only = "--no-remote" not in args
dry_run     = "--dry-run" in args
no_apply    = "--no-apply" in args
verify      = "--verify" in args  # confirma con una request extra que la oferta siga viva
# Por defecto NO se generan cartas (cuesta API DeepSeek y el ~95% nunca se usa).
# Descubrir lista candidatas gratis -> revisar links -> generar on-demand con
# gen_cover.py. --with-cover fuerza el comportamiento viejo (carta para todas).
with_cover  = "--with-cover" in args
if with_cover:
    from src import cover  # import lazy: solo necesita anthropic si se piden cartas

# ---------------------------------------------------------------------------
# Descubrir ofertas
# ---------------------------------------------------------------------------
print("=" * 64)
print("DESCUBRIMIENTO DE OFERTAS")
print("=" * 64)

discovered: list[dict] = []

if not only_board or only_board == "getonbrd":
    print("\nGetOnBrd (getonbrd.com)...")
    gob_jobs = boards.discover_getonbrd(remote_only=remote_only, max_pages=3)
    print(f"  {len(gob_jobs)} ofertas encontradas")
    discovered.extend(gob_jobs)

if not only_board or only_board == "himalayas":
    print("\nHimalayas (himalayas.app)...")
    him_jobs = boards.discover_himalayas()
    him_global = boards.filter_himalayas_location(him_jobs)
    print(f"  {len(him_jobs)} ofertas → {len(him_global)} sin restricción de país")
    discovered.extend(him_global)

if not only_board or only_board == "weworkremotely":
    print("\nWe Work Remotely (weworkremotely.com)...")
    wwr_jobs = boards.discover_weworkremotely()
    wwr_global = boards.filter_global_remote(wwr_jobs)
    print(f"  {len(wwr_jobs)} ofertas → {len(wwr_global)} accesibles desde Ecuador")
    discovered.extend(wwr_global)

if not only_board or only_board == "4dayweek":
    print("\n4 Day Week (4dayweek.io)...")
    fdw_jobs = boards.discover_4dayweek()
    fdw_global = boards.filter_global_remote(fdw_jobs)
    print(f"  {len(fdw_jobs)} ofertas → {len(fdw_global)} accesibles desde Ecuador")
    discovered.extend(fdw_global)

if not only_board or only_board == "remotefirstjobs":
    print("\nRemote First Jobs (remotefirstjobs.com)...")
    rfj_jobs = boards.discover_remotefirstjobs()
    rfj_global = boards.filter_global_remote(rfj_jobs)
    print(f"  {len(rfj_jobs)} ofertas → {len(rfj_global)} accesibles desde Ecuador")
    discovered.extend(rfj_global)

if not only_board or only_board == "workingnomads":
    print("\nWorking Nomads (workingnomads.com)...")
    wn_jobs = boards.discover_workingnomads()
    wn_global = boards.filter_global_remote(wn_jobs)
    print(f"  {len(wn_jobs)} ofertas → {len(wn_global)} accesibles desde Ecuador")
    discovered.extend(wn_global)

if not only_board or only_board == "remotive":
    print("\nRemotive (remotive.com)...")
    remotive_jobs = boards.discover_remotive()
    remotive_global = boards.filter_global_remote(remotive_jobs)
    print(f"  {len(remotive_jobs)} ofertas → {len(remotive_global)} con acceso global/LATAM")
    discovered.extend(remotive_global)

if not only_board or only_board == "linkedin":
    print("\nLinkedIn (jobs-guest)...")
    li_jobs = boards.discover_linkedin(remote_only=remote_only)
    li_global = boards.filter_global_remote(li_jobs)
    print(f"  {len(li_jobs)} ofertas → {len(li_global)} accesibles desde Ecuador")
    discovered.extend(li_global)

if not only_board or only_board == "linkedin-auth":
    print("\nLinkedIn AUTENTICADO (sesion guardada)...")
    lia_jobs = boards.discover_linkedin_auth(remote_only=remote_only)
    lia_global = boards.filter_global_remote(lia_jobs)
    print(f"  {len(lia_jobs)} ofertas → {len(lia_global)} accesibles desde Ecuador")
    discovered.extend(lia_global)

if not only_board or only_board == "hackernews":
    print("\nHacker News (Who is hiring)...")
    hn_jobs = boards.discover_hackernews()
    hn_global = boards.filter_global_remote(hn_jobs)
    print(f"  {len(hn_jobs)} ofertas → {len(hn_global)} accesibles desde Ecuador")
    discovered.extend(hn_global)

# Canal local: sin filter_global_remote — el pais del candidato es valido
if not only_board or only_board in ("linkedin-local", "local"):
    print("\nLinkedIn LOCAL (canal pais del candidato)...")
    lil_jobs = boards.discover_linkedin_local()
    print(f"  {len(lil_jobs)} ofertas encontradas")
    discovered.extend(lil_jobs)

if not only_board or only_board in ("computrabajo", "local"):
    print("\nComputrabajo (canal local)...")
    ct_jobs = boards.discover_computrabajo()
    print(f"  {len(ct_jobs)} ofertas encontradas")
    discovered.extend(ct_jobs)

if not only_board or only_board in ("multitrabajos", "local"):
    print("\nMultitrabajos (canal local, Playwright)...")
    mt_jobs = boards.discover_multitrabajos()
    print(f"  {len(mt_jobs)} ofertas encontradas")
    discovered.extend(mt_jobs)

if not only_board or only_board == "wellfound":
    print("\nWellfound (wellfound.com)...")
    wf_jobs = boards.discover_wellfound()
    print(f"  {len(wf_jobs)} ofertas encontradas")
    discovered.extend(wf_jobs)

if not only_board or only_board == "glovo":
    print("\nGlovo Careers (careers.glovoapp.com)...")
    glovo_jobs = boards.discover_glovo(tech_only=True)
    print(f"  {len(glovo_jobs)} ofertas encontradas")
    discovered.extend(glovo_jobs)

# Filtros en cascada
tech_jobs   = boards.filter_tech(discovered)
junior_jobs = boards.filter_junior(tech_jobs)
clean_jobs  = boards.filter_role_noise(junior_jobs)
clean_jobs  = boards.dedup_by_company_title(clean_jobs)
# filter_entry_level necesita la descripcion; se aplica despues de scraping

print(
    f"\nTotal: {len(discovered)} → {len(tech_jobs)} técnicas "
    f"→ {len(junior_jobs)} sin senior/lead "
    f"→ {len(clean_jobs)} sin ruido/duplicados\n"
)

if not clean_jobs:
    print("[!] No se encontraron ofertas. Verifica conexión o estructura del board.")
    sys.exit(0)

# ---------------------------------------------------------------------------
# CV
# ---------------------------------------------------------------------------
cv = profile.load()
if "error" in cv:
    print(f"[!] Error cargando CV: {cv['error']}")
    sys.exit(1)
print(f"CV cargado: {len(cv.get('techs', []))} tecnologias\n")

# ---------------------------------------------------------------------------
# Pipeline: scrape descripcion → filtro exp → match → cover letter → apply
# ---------------------------------------------------------------------------
results      = []  # cartas generadas y con URL ATS resuelta
no_ats_urls  = []  # jobs sin URL ATS detectable (aplica manual)

for job in clean_jobs:
    print("=" * 64)
    print(f"[{job['source'].upper():10}] {job['title']}")
    print(f"  URL: {job['url']}")
    if job.get("location_required"):
        loc_warn = " [!]" if job.get("location_warning") else ""
        print(f"  Ubicacion: {job['location_required']}{loc_warn}")

    # Saltar si ya fue postulada
    if job["url"] in applied_urls:
        print("  [✓] Ya postulada — omitida")
        continue

    # Saltar si ya se listo en una corrida de descubrimiento previa
    if job["url"] in seen_urls:
        print("  [=] Ya listada antes — omitida (usa gen_cover.py si querés su carta)")
        continue

    # Scrapear descripcion completa si la API no la trajo
    if not job.get("description") or len(job["description"]) < 200:
        print("  Scrapeando descripcion...")
        detail = fetch_job(job["url"])
        if "error" in detail:
            print(f"  [!] Scraping fallido: {detail['error']}")
            continue
        job["description"] = detail.get("description", "")
        if not job.get("company") and detail.get("company"):
            job["company"] = detail["company"]
        if not job.get("title") or job["title"] == "Sin titulo":
            job["title"] = detail.get("title", job["title"])

    if not job.get("description"):
        print("  [!] Sin descripcion — omitida")
        continue

    # Filtro de experiencia requerida en descripcion
    filtered = boards.filter_entry_level([job])
    if not filtered:
        print("  [x] Requiere 3+ años de experiencia — omitida")
        continue

    # Verificar remote si no vino del listing
    if job.get("remote") is None:
        job["remote"] = bool(boards.REMOTE_FILTER.search(job["description"]))
    # Canal local: presencial/hibrido en el pais del candidato es valido
    if remote_only and job.get("remote") is False and job.get("canal") != "local":
        print("  [x] No es remoto — omitida")
        continue

    # Match contra CV
    match = matcher.score(job, cv)
    print(f"  Match: {match['score']}% ({match['fit']}) — techs: {match['matched_techs'][:6]}")
    if match["fit"] == "baja":
        print("  [x] Compatibilidad baja — omitida")
        continue

    # Verificacion opcional de vigencia (request extra por candidata)
    # NO se marca como vista si esta muerta: un falso positivo puede reaparecer
    if verify and boards.is_job_dead(job["url"]):
        print("  [x] Oferta expirada/cerrada (--verify) — omitida")
        continue

    # Candidata valida → marcar como vista para no re-listarla mañana
    applied.mark_seen(job["url"])
    seen_urls.add(job["url"])

    # URL del formulario GetOnBrd (gratis de construir; util para listar y aplicar)
    if job["source"] == "getonbrd":
        job["ats_url"] = boards.getonbrd_apply_url(job["url"])
        job["ats_platform"] = "getonbrd"

    # Generar carta SOLO si se pidio (--with-cover). Por defecto solo se lista:
    # cuesta API y el ~95% nunca se usa. Carta on-demand via gen_cover.py.
    carta = None
    out_path = None
    if with_cover:
        print("  Generando carta...")
        try:
            carta = cover.generate(job, cv)
        except Exception as e:
            print(f"  [!] Error generando carta: {e}")
            carta = None
        if carta:
            url_id = job["url"].rstrip("/").split("/")[-1]
            slug = re.sub(r"[^a-z0-9]+", "_", url_id.lower())[:55].strip("_")
            out_path = os.path.join(OUT_DIR, f"disc_{slug}.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(carta)
            print(f"  Carta guardada: output/cartas/disc_{slug}.txt")
            applied.mark_applied(job["url"])
            applied_urls.add(job["url"])
    else:
        print("  [+] Candidata listada (sin carta — gen_cover.py para generar)")

    results.append({"job": job, "match": match, "carta": carta, "path": out_path})

# ---------------------------------------------------------------------------
# Volcar candidatas a JSON para la fase on-demand (gen_cover.py --from-json)
# ---------------------------------------------------------------------------
if results:
    cand_path = os.path.join(OUT_DIR, f"candidates_{datetime.date.today()}.json")
    new_cands = [{"url": r["job"]["url"], "title": r["job"]["title"],
                  "company": r["job"].get("company", ""),
                  "source": r["job"]["source"],
                  "canal": r["job"].get("canal", "remoto"),
                  "location": r["job"].get("location_required", ""),
                  "match": r["match"]["score"],
                  "description": r["job"].get("description", "")[:3000]}
                 for r in results]
    # Merge con corridas previas del mismo dia (ej. un board y luego otro):
    # sin esto, cada corrida sobrescribia el JSON y perdia las anteriores
    if os.path.exists(cand_path):
        with open(cand_path, encoding="utf-8") as f:
            old = json.load(f)
        new_urls = {c["url"] for c in new_cands}
        new_cands = [c for c in old if c["url"] not in new_urls] + new_cands
    with open(cand_path, "w", encoding="utf-8") as f:
        json.dump(new_cands, f, ensure_ascii=False, indent=2)
    api_tag = "con API (cartas generadas)" if with_cover else "0 API (solo listado)"
    print(f"\nCandidatos guardados: {cand_path}  ({len(results)} ofertas, {api_tag})")
    print(f"  Generá carta on-demand: python gen_cover.py --from-json {cand_path} --pick <n>")

# ---------------------------------------------------------------------------
# Auto-apply (Workable / Greenhouse — plataformas soportadas)
# Requiere cartas generadas → solo con --with-cover.
# ---------------------------------------------------------------------------
if with_cover and not no_apply:
    supported = ("workable", "greenhouse", "getonbrd")
    to_apply = [r for r in results if r["job"].get("ats_platform") in supported]
    manual   = [r for r in results if r["job"].get("ats_platform") not in supported]

    if to_apply:
        print(f"\n{'='*64}")
        mode = "DRY-RUN (formulario listo, NO se envía)" if dry_run else "POSTULACION REAL"
        print(f"AUTO-APPLY — {len(to_apply)} postulaciones — {mode}")
        print("=" * 64)

        from playwright.sync_api import sync_playwright

        gob_session = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".gob_session.json")
        has_gob_session = os.path.exists(gob_session)
        if not has_gob_session:
            print("[!] Sin sesión GetOnBrd guardada.")
            print("    Corre: python setup_gob_session.py")
            print("    Los jobs de GetOnBrd se moverán a aplicar manual.\n")

        cv_abs = apply_ats.cv_path_resolve("cv_path")

        with sync_playwright() as pw:
            # Contexto con sesión GetOnBrd (si existe)
            if has_gob_session:
                context = pw.chromium.launch(
                    headless=True, args=["--no-sandbox"]
                ).new_context(storage_state=gob_session)
            else:
                browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
                context = browser.new_context()

            for r in to_apply:
                j = r["job"]
                platform = j.get("ats_platform", "")
                url = j.get("ats_url") or j["url"]

                # Saltar GetOnBrd si no hay sesión
                if platform == "getonbrd" and not has_gob_session:
                    manual.append(r)
                    continue

                print(f"\nPostulando: {j['title']} [{platform}]")
                print(f"  URL: {url}")

                result = apply_ats.apply_with_context(context, url, r["carta"], cv_abs, dry_run=dry_run)

                if result.get("ready"):
                    # La page puede venir embebida en el result (getonbrd)
                    page = result.pop("page", None)
                    if dry_run:
                        print("  Dry-run: formulario listo, NO se envió")
                        if page:
                            page.close()
                    else:
                        target_page = page or context.pages[-1]
                        submitted = False
                        for sel in [
                            'button[type="submit"]:has-text("Submit")',
                            'button[type="submit"]:has-text("Enviar")',
                            'button[type="submit"]:has-text("Apply")',
                            'button[type="submit"]:has-text("Postular")',
                            'input[type="submit"]',
                            'button[type="submit"]',
                        ]:
                            btn = target_page.query_selector(sel)
                            if btn and btn.is_visible():
                                btn.click()
                                target_page.wait_for_timeout(3000)
                                submitted = True
                                print(f"  Enviado via {sel}")
                                break
                        if not submitted:
                            print("  [!] No se encontró botón submit")
                        if page:
                            page.close()

                if result.get("ok"):
                    print("  OK")
                else:
                    print(f"  Error: {result.get('error', '?')}")

    if manual:
        print(f"\n--- {len(manual)} job(s) para aplicar manualmente ---")
        for r in manual:
            j = r["job"]
            print(f"  {j['title']:45} → {j.get('ats_url') or j['url']}")

# ---------------------------------------------------------------------------
# Resumen final
# ---------------------------------------------------------------------------
print("\n" + "=" * 64)
_kind = "cartas" if with_cover else "candidatas listadas"
print(f"RESUMEN: {len(results)} {_kind} / {len(junior_jobs)} candidatas procesadas")
for r in results:
    j = r["job"]
    if j.get("canal") == "local":
        remote_tag = "LOCAL"
    else:
        remote_tag = "REMOTO" if j.get("remote") else "presencial"
    company    = str(j.get("company") or "?")
    loc        = j.get("location_required", "")
    loc_tag    = f" [{loc}]" if loc and loc.lower() not in ("worldwide", "") else ""
    print(
        f"  [{j['source']:10}] {company:20} "
        f"{j['title'][:38]:38} {r['match']['score']}%  {remote_tag}{loc_tag}"
    )
