# CLAUDE.md — ApplyJob Project Context

## Overview

ApplyJob automatiza postulaciones laborales. Pipeline: extraer ofertas → matchear contra perfil → generar cover letter con DeepSeek → postular en ATS via Playwright.

## Key Files

- `main.py` — orquestador CLI del pipeline clasico (scrape → match → cover → send)
- `src/scraper.py` — extrae info de ofertas desde URLs (httpx + Playwright fallback)
- `src/matcher.py` — calcula % de compatibilidad oferta vs perfil
- `src/cover.py` — genera carta personalizada con DeepSeek Flash (via Anthropic SDK)
- `src/apply_ats.py` — auto-postulacion en ATS con Playwright; soporta Workable, Greenhouse, GetOnBrd (con sesion)
- `src/boards.py` — descubre ofertas desde tableros: GetOnBrd, Himalayas, We Work Remotely (RSS), 4 Day Week (API), Remote First Jobs (API), Working Nomads (API), Remotive, Glovo; filtros junior/entry-level/global-remote
- `src/letter_to_pdf.py` — convierte cartas .txt a PDF via python-docx + LibreOffice
- `src/sender.py` — envia carta por Gmail SMTP
- `src/inbox.py` — lector IMAP para boletines de ofertas
- `run_batch.py` — batch: resuelve short URLs, scrapea con Playwright y genera cartas
- `run_manual.py` — batch con descripciones manuales (cuando el scraping falla)
- `run_discover.py` — pipeline completo: descubre boards → filtra → genera cartas → auto-aplica
- `setup_gob_session.py` — guarda sesion GetOnBrd una vez (magic link); requerido para auto-apply en GetOnBrd
- `profile/cv.md` — perfil del candidato en español (stack, experiencia, skills)
- `profile/cv_en.md` — perfil del candidato en INGLES (para ofertas en ingles, ej. Canonical)
- `profile/CV_Mickaell_Moran.pdf` — CV en PDF (español)
- `profile/CV_Mickaell_Moran_EN.pdf` — CV en PDF (ingles, para Canonical y ofertas EN)
- `output/cartas/` — cartas generadas (GITIGNORED: contienen datos de contacto reales/PII)
- `output/canonical_form_answers.txt` — respuestas reutilizables para formularios Canonical (GITIGNORED)
- `.gob_session.json` — sesion guardada de GetOnBrd para auto-apply (GITIGNORED)
- `samples/` — boletines de ofertas guardados

## ATS Auto-Apply Module (`src/apply_ats.py`)

Usa Playwright headless Chromium para llenar formularios de postulacion.

**Plataformas soportadas:**
- Workable ✅ — Platzi, Canonical, Loft
- Greenhouse ✅ — Canonical (handler completo; pendiente test real)
- GetOnBrd ✅ — requiere sesion guardada via `setup_gob_session.py`; usa `apply_getonbrd()` con storage_state
- Teamtailor ❌ — Global66, Loft (PROBADO 2026-05-31: NO funciona; cookie wall + timeout en dry_run)
- Ashby 📋 — Addi (pendiente)
- Workday 📋 — Amadeus, Oracle, BBVA (pendiente; requiere crear cuenta/login, anti-bot)
- Sitios propios 📋 — Addi (custom, caso por caso)

**Funcionamiento:**
1. Navega a la URL de la oferta
2. Acepta cookies
3. Busca y clickea boton "Apply"
4. Llena campos (nombre, email, telefono, ubicacion, linkedin)
5. Sube CV en PDF
6. Pega cover letter en textarea
7. Click submit (dry_run=True para probar sin enviar)

**Modo dry_run:** `run(jobs_with_letters, dry_run=True)` — llena formulario pero NO hace submit.

**Candidate data:** El dict `CANDIDATE` se carga 100% desde `.env` (CANDIDATE_NAME, _PHONE, _LOCATION, _CITY, _COUNTRY, _LINKEDIN, _GITHUB, _WEBSITE + GMAIL_USER, CV_PATH, CV_PATH_EN). Sin PII hardcodeada en el repo.

**Soporte bilingüe:** `run(jobs_with_letters, lang="en")` usa `CV_PATH_EN` (PDF EN) en lugar del PDF ES. Default `lang="es"`.

## CV / Profile

El perfil esta en `profile/cv.md`. Se extraen tecnologias via regex de las secciones "Stack" y "Skills".

**Techs extraidos:** python, django, fastapi, react, typescript, node.js, flutter, dart, postgresql, docker, linux, git, firebase, rest, api, y mas (25 total).

## Matcher

`matcher.score(job, cv)` → compara tech keywords contra titulo+descripcion de la oferta.
- Score = (keywords matcheados / total keywords) * 100
- >40% = alta, 20-40% = media, <20% = baja (descartada)

## Cover Letter Generation

`cover.generate(job, cv, lang="es")` → usa DeepSeek Flash via Anthropic SDK.
- Prompt incluye: titulo oferta, empresa, descripcion, datos del candidato, perfil completo
- `lang="es"` (default) genera en español; `lang="en"` en ingles (para Canonical y ofertas en ingles)
- Output: carta profesional, sin emojis, <250 palabras, con datos de contacto reales

**OJO con ofertas que prohiben IA:** Canonical declara explicitamente que el uso de IA/contenido
generado descalifica la solicitud. Para esas, el candidato debe escribir carta y respuestas con
sus propias palabras (traducir el CV factual si es aceptable). No pegar texto generado por IA.

## .env Required

```
DEEPSEEK_API_KEY=sk-...
GMAIL_USER=tu-correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
CV_PATH=./profile/CV_Mickaell_Moran.pdf
CV_PATH_EN=./profile/CV_Mickaell_Moran_EN.pdf

# Datos del candidato (apply_ats.py los usa para llenar formularios ATS)
CANDIDATE_NAME=...
CANDIDATE_PHONE=...
CANDIDATE_LOCATION=...
CANDIDATE_CITY=...
CANDIDATE_COUNTRY=...
CANDIDATE_LINKEDIN=...
CANDIDATE_GITHUB=...
CANDIDATE_WEBSITE=

# GetOnBrd (opcional — default: .gob_session.json en raiz del proyecto)
GETONBRD_SESSION_PATH=./.gob_session.json
```

## Discovery Pipeline (`run_discover.py`)

Pipeline de descubrimiento multi-board → filtrado → generacion de cartas. Postulacion MANUAL.

```bash
.venv/bin/python3 run_discover.py --no-apply        # todos los boards (default)
.venv/bin/python3 run_discover.py getonbrd          # solo GetOnBrd
.venv/bin/python3 run_discover.py himalayas         # solo Himalayas
.venv/bin/python3 run_discover.py weworkremotely    # solo We Work Remotely
.venv/bin/python3 run_discover.py 4dayweek          # solo 4 Day Week
.venv/bin/python3 run_discover.py remotefirstjobs   # solo Remote First Jobs
.venv/bin/python3 run_discover.py workingnomads     # solo Working Nomads
```

**Boards activos:**
- GetOnBrd        — ~18 cartas/corrida (LATAM, API JSON, remoto real)
- Himalayas       — ~11 cartas/corrida (global, API JSON, filtro Entry+Mid nativo)
- We Work Remotely — RSS público, ~27 candidatas, jobs de calidad worldwide
- 4 Day Week      — API JSON, remote+entry/mid, ~25 candidatas por corrida
- Remote First Jobs — API JSON, entry/middle/intern, ~168 candidatas por corrida
- Working Nomads  — API JSON, 2 categorías, ~3-5 cartas/corrida
- Total tipico: 50-80 cartas/corrida (todos los boards)

**Filtros en cascada:**
1. Keywords tecnicas en titulo (`TECH_FILTER`)
2. Sin senior/lead/architect/ssr en titulo (`_SENIOR_EXCLUDE`)
3. Sin "3+ años de experiencia" en descripcion (`_EXP_EXCLUDE`)
4. [Himalayas] `worldwide=true` en API + exclusion por URL de país (`_HIMALAYAS_URL_COUNTRY`)
5. [WWR/4DW/RFJ/WN] `filter_global_remote` — excluye paises sin Ecuador, marca ambiguos con `[!]`

**Jobs con [!] en location:** son ambiguos (ciudad en vez de pais) — revisarlos antes de postular.

**GetOnBrd session setup (una vez):**
```bash
.venv/bin/python3 setup_gob_session.py
```
Abre browser visible → ingresas email → GetOnBrd manda magic link → copiás la URL del link (clic derecho, NO abrirlo) → la pegás en la terminal → sesión guardada en `.gob_session.json`.
IMPORTANTE: el magic link debe abrirse dentro de Playwright (pegado en terminal), NO en el browser normal.

## `src/boards.py` — Board Scrapers

- `discover_getonbrd(remote_only, max_pages)` — API JSON (`/api/v0/categories/programming/jobs`); excluye IDs seniority 4=Senior y 5=Lead
- `discover_himalayas()` — API JSON pública (`/jobs/api?worldwide=true`); paginado, filtra Entry+Mid-level por seniority field, excluye país en URL; headers mínimos (sin Accept-Language → Cloudflare 403)
- `discover_weworkremotely()` — RSS XML (3 feeds: programming, full-stack, devops); campo `region` → location_required; título "Company: Job Title" → empresa+puesto
- `discover_4dayweek(max_pages)` — API JSON; params `work_arrangement=remote&level=entry,mid`; ~25 jobs/página; campo `locations[0].country` → location_required
- `discover_remotefirstjobs(max_pages)` — API JSON; 6 queries tech, 2 páginas/query; filtra seniority `entry_level/middle/intern`; campo `locations` → location_required
- `discover_workingnomads()` — API JSON (programming + devops-sysadmin); campo `location` → location_required
- `discover_wellfound()` — Playwright headless=False + intercepción GraphQL; requiere `.wellfound_session.json`; DESHABILITADO por default (captcha frecuente + pocos resultados Ecuador)
- `filter_himalayas_location(jobs)` — passthrough (worldwide=true ya filtra en API)
- `discover_remotive()` — API JSON (actualmente limitada a ~28 jobs fijos en tier free)
- `discover_glovo(tech_only)` — Playwright en careers.glovoapp.com (0 resultados, pendiente fix)
- `filter_tech(jobs)` — keywords tecnicas en titulo
- `filter_junior(jobs)` — excluye senior/lead/ssr/etc en titulo
- `filter_entry_level(jobs)` — excluye si descripcion pide 3+ años
- `filter_global_remote(jobs)` — excluye country-restricted (USA/UK/etc); agrega `location_warning` a los ambiguos
- `getonbrd_apply_url(url)` — retorna `{url}/applications/new`
- `resolve_apply_url(url)` — encuentra URL ATS externa via Playwright

## Current State (2026-06-09)

- CV bilingüe completo: `profile/cv.md` (ES) + `profile/cv_en.md` (EN) + PDFs en ambos idiomas.
- `cover.generate` soporta `lang="es"/"en"`. `apply_ats.run()` soporta `lang="en"` para subir CV EN.
- `src/letter_to_pdf.py` — genera PDFs de cartas desde .txt via python-docx + LibreOffice.
- `src/cover.py` actualizado (2026-06-06): reglas de honestidad en prompt ES+EN, lista de techs prohibidas, deteccion automatica de tech desconocida en descripcion, perfil completo sin truncado.
- Canonical x4 rechazadas (2026-06-03): Graduate Software Engineer / Software Engineer Python Cloud / Junior Software Developer Observability / Junior Ubuntu Software Engineer. Todas filtradas en primera ronda automatica. Reaplicar en 6 meses.
- `profile/getonboard_bio.txt` — textos del perfil GetOnBoard en ES+EN (gitignored).
- `profile/postulaciones.md` — tracker de postulaciones enviadas (gitignored).
- Decision de flujo (2026-06-06): `run_discover.py --no-apply` para filtrar y generar cartas; postulaciones se envian MANUALMENTE. No usar auto-apply para envios reales.
- Restriccion del candidato: SOLO remoto-real (estudiante en Guayaquil, sin reubicacion).
- Postulaciones enviadas al 2026-06-09: 17 total (4 Canonical rechazadas, 13 activas). Las 3 de Bluelight Consulting via Himalayas recibieron confirmacion inmediata via Lever. Tritone Analytics tambien via GetOnBoard.
- `clean_letters.py` — archiva cartas del dia en `output/cartas/archive/YYYY-MM-DD/`. Correr cada noche.
- Boards descartados: RemoteOK (paywall candidatos), Wellfound (DataDome+CF, scraping inviable + pocos resultados Ecuador), Jobicy (401), Torre.co (401), Arbeitnow (aleman), Remotive (28 jobs fijos), Jobgether (403), Authentic Jobs (RSS vacio), YC Work at a Startup (sin API publica).
- Patron Himalayas: muchos jobs "worldwide" tienen pais en la URL — filtro `_HIMALAYAS_URL_COUNTRY` los excluye.
- Boards agregados (2026-06-07): Working Nomads (API JSON, 39 raw), We Work Remotely (RSS, 73 raw), 4 Day Week (API JSON, 150 raw remote entry/mid), Remote First Jobs (API JSON, 425 raw entry/middle/intern). Total candidatas antes de match: ~220/corrida.
- `run_batch.py` reescrito (2026-06-07): parsea boletin JuniorJobs (canal Telegram dominical), detecta banderas de pais, extrae empresa+titulo, corre mismo pipeline que run_discover.py. Usar cada domingo con el texto del boletin.
- `_LOCATION_OK` regex: NO incluir "Remote" suelto — "Japan - Remote" lo matchea como falso positivo. Solo Worldwide/Anywhere/Global/Americas/LATAM/International.
- `filter_global_remote` bug corregido (2026-06-07): referencia a `_REMOTEOK_LOC_EXCLUDE` inexistente eliminada.
- Portafolio actualizado (2026-06-08): 5 proyectos nuevos en ES+EN — MotoVox (Flutter+C+WebRTC+FFI), Flores Eternas (Node.js+SRI Ecuador), Taller App (Node.js+React freelance), ApplyJob (Python+Playwright+AI), QR Shield (Python+Chrome Extension). GitHub links agregados a Centro Tia Glenda, EcuaInventario y Facturador.
- CV React (`lib/cv/content.ts`) actualizado (2026-06-08): bullet Flores Eternas en Freelance + MotoVox como 5to proyecto. PDFs ES/EN regenerados.
- GitHub limpiado (2026-06-08): READMEs y About descriptions en todos los repos publicos. TIER 1: TiaGlenda (prod), EcuaInventario, Facturador, SimuladorExamenes. TIER 2: MotoVox, TallerApp. TIER 3: qr-shield, mcp-context-server (3★), ApplyJob.
- Output files (gitignored): `output/sezzle_latam_answers.txt`, `output/monterail_pick_one_tool.txt`, `output/tritone_why.txt`, `output/tritone_why_en.txt`, `output/getonbrd_perfil_actualizado.txt`, `output/getonbrd_perfil_actualizado_en.txt`.
- Observacion del pipeline (2026-06-09): de 256 cartas generadas, la mayoria son senior/geo-restringidas (India, UK, US, LATAM especifico sin Ecuador). Los validos aplicados: Bluelight x3, Sezzle, Monterail, Tritone, EasyAudit AI, BC Tecnologia x3, Idealista, Designcafe. Pattern: Remote First Jobs genera muchos falsos positivos de seniority; revisar individualmente antes de postular.

## Common Issues

- Scraper falla con short URLs (juniorjobs.short.gy) porque redirigen a JS-heavy ATS
- Solucion: resolver short URLs con httpx.head() primero, luego scrapear URL final con Playwright
- Matcher da scores bajos si la descripcion extraida no contiene keywords tecnicas
- Teamtailor tiene cookie wall que bloquea contenido → `apply_teamtailor` da Timeout/no encuentra boton (probado 2026-05-31, sigue roto)
- Workable requiere manejar firstname/lastname separados
- Muchas ofertas "100% remoto" son remoto DENTRO del pais (ej. Loft Brasil = CLT + portugués); verificar antes de aplicar
- Workday/Oracle exigen crear cuenta con login + verificación email → no automatizables de forma confiable
- Glovo Careers (careers.glovoapp.com) devuelve 0 resultados — React SPA, los links de ofertas no se encuentran con Playwright ni httpx
- GetOnBrd auto-apply requiere sesion activa en `.gob_session.json`. Magic link ES DE UN SOLO USO y expira en ~5 min. Flujo correcto: correr `setup_gob_session.py` → solicitar magic link → en el correo, clic derecho sobre el boton/link → "Copiar dirección" → pegarlo en la terminal del script. NO hacer clic en el link antes de pegarlo (invalida el link al abrirlo en el browser real).
- GetOnBrd formulario es de 3 pasos: step 1 (cover letter Trix + nivel inglés), step 2 (phone/linkedin/github/reason), step 3 (preview). El submit de cada paso usa fetch() con credentials:include porque el Stimulus controller bloquea form.submit() nativo. GetOnBrd auto-crea drafts al navegar a /applications/new; el fetch bypassea eso.
- GetOnBrd magic link puede pegarse directamente en `setup_gob_session.py` o ejecutar `python3 -c "..."` headless para autenticar sin browser visible (ver sesion 2026-06-05).
