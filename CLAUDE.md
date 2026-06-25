# CLAUDE.md — ApplyJob Project Context

## Overview

ApplyJob automatiza postulaciones laborales. Pipeline: extraer ofertas → matchear contra perfil → generar cover letter con DeepSeek → postular en ATS via Playwright.

## Key Files

- `main.py` — orquestador CLI del pipeline clasico (scrape → match → cover → send)
- `src/scraper.py` — extrae info de ofertas desde URLs (httpx + Playwright fallback)
- `src/matcher.py` — calcula % de compatibilidad oferta vs perfil
- `src/cover.py` — genera carta personalizada con DeepSeek Flash (via Anthropic SDK)
- `src/apply_ats.py` — auto-postulacion en ATS con Playwright; soporta Workable, Greenhouse, GetOnBrd (con sesion)
- `src/boards.py` — descubre ofertas desde tableros: GetOnBrd, Himalayas, We Work Remotely (RSS), 4 Day Week (API), Remote First Jobs (API), Working Nomads (API), LinkedIn (jobs-guest), Hacker News (Who is hiring, API Algolia), Remotive, Glovo; filtros junior/entry-level/global-remote
- `src/letter_to_pdf.py` — convierte cartas .txt a PDF via python-docx + LibreOffice
- `src/sender.py` — envia carta por Gmail SMTP
- `src/inbox.py` — lector IMAP para boletines de ofertas
- `run_batch.py` — batch: resuelve short URLs, scrapea con Playwright y genera cartas
- `run_manual.py` — batch con descripciones manuales (cuando el scraping falla)
- `run_discover.py` — pipeline de descubrimiento: descubre boards → filtra → match → **LISTA candidatas (0 API)** y vuelca JSON. Cartas opt-in con `--with-cover`
- `gen_cover.py` — genera UNA carta on-demand tras revisar el link a mano (por `<url>`, `--desc`, o `--from-json <candidates.json> --pick <n>`). El ÚNICO script que gasta API por carta real
- `src/applied.py` — tracking compartido de URLs: `applied_urls.txt` (con carta/postuladas) + `output/seen_discovered.txt` (ya listadas, evita re-listar). Usado por `run_discover.py` y `gen_cover.py`
- `setup_gob_session.py` — guarda sesion GetOnBrd una vez (magic link); requerido para auto-apply en GetOnBrd
- `profile/cv.md` — perfil del candidato en español (stack, experiencia, skills)
- `profile/cv_en.md` — perfil del candidato en INGLES (para ofertas en ingles, ej. Canonical)
- `profile/cv_es.pdf` — CV en PDF formato Harvard (español); ruta en `CV_PATH` del .env
- `profile/cv_en.pdf` — CV en PDF formato Harvard (ingles); ruta en `CV_PATH_EN` del .env
- `profile/cv_es.docx` — fuente editable del CV ES (formato Harvard)
- `profile/cv_en.docx` — fuente editable del CV EN (formato Harvard)
- `profile/generate_cv.py` — script que genera los .docx desde cero (python-docx); correr para regenerar
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

**Candidate data:** El dict `CANDIDATE` se carga 100% desde `.env` (CANDIDATE_NAME, _PHONE, _LOCATION, _CITY, _COUNTRY, _LINKEDIN, _GITHUB, _WEBSITE + GMAIL_USER, CV_PATH, CV_PATH_EN). Sin PII hardcodeada en el repo. Fallbacks genéricos (no personales) si falta la var.

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
- Todos los datos del candidato (nombre, email, teléfono, linkedin, github, ubicacion) se extraen del `profile` dict o del `.env`. Sin fallbacks personales hardcodeados.
- **Prompt ordenado para cache de DeepSeek (2026-06-25):** lo CONSTANTE (reglas + datos candidato + perfil) va primero, la OFERTA variable (incl. `unknown_note`, que depende del job) al FINAL. DeepSeek cachea por prefijo común → cartas del mismo idioma reusan el prefijo (~80-90% menos input). NO meter nada dependiente del job en el bloque constante o se rompe el cache.

**OJO con ofertas que prohiben IA:** Canonical declara explicitamente que el uso de IA/contenido
generado descalifica la solicitud. Para esas, el candidato debe escribir carta y respuestas con
sus propias palabras (traducir el CV factual si es aceptable). No pegar texto generado por IA.

## .env Required

```
DEEPSEEK_API_KEY=sk-...
GMAIL_USER=tu-correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
CV_PATH=./profile/cv.pdf
CV_PATH_EN=./profile/cv_en.pdf

# Datos del candidato — usados en cartas (cover.py) y formularios ATS (apply_ats.py)
CANDIDATE_NAME=...
CANDIDATE_PHONE=...
CANDIDATE_LOCATION=...      # alternativa a CITY+COUNTRY
CANDIDATE_CITY=...
CANDIDATE_COUNTRY=...
CANDIDATE_LINKEDIN=...
CANDIDATE_GITHUB=...
CANDIDATE_WEBSITE=

# Región geográfica — controla filter_global_remote y filter_himalayas_location
# Opciones: LATAM (default), EUROPE, ASIA, USA, GLOBAL
CANDIDATE_REGION=LATAM

# GetOnBrd (opcional — default: .gob_session.json en raiz del proyecto)
GETONBRD_SESSION_PATH=./.gob_session.json
```

## Discovery Pipeline (`run_discover.py`)

Pipeline de descubrimiento multi-board → filtrado → match → **LISTA candidatas**. Postulacion MANUAL.

**Flujo de costo optimizado (refactor 2026-06-25):** descubrir ya NO genera cartas
por defecto (gastaba API en ~40 cartas/corrida cuando solo se usan 1-3). Ahora:
1. **Descubrir** (0 API): lista candidatas + vuelca `output/cartas/candidates_AAAA-MM-DD.json`.
2. **Revisar los links a mano** (lo hace el candidato).
3. **Generar carta on-demand** SOLO para la elegida: `gen_cover.py`.

```bash
# 1) Descubrir y listar (0 API)
.venv/bin/python3 run_discover.py --no-apply        # todos los boards (default)
.venv/bin/python3 run_discover.py getonbrd          # un board (getonbrd|himalayas|
                                                    #   weworkremotely|4dayweek|
                                                    #   remotefirstjobs|workingnomads|
                                                    #   linkedin|hackernews)
.venv/bin/python3 run_discover.py --with-cover      # (opt-in) ademas genera cartas — gasta API

# 2) Generar carta on-demand tras revisar el link
.venv/bin/python3 gen_cover.py https://url-de-la-oferta            # scrapea la URL
.venv/bin/python3 gen_cover.py --from-json output/cartas/candidates_AAAA-MM-DD.json          # lista para elegir
.venv/bin/python3 gen_cover.py --from-json output/cartas/candidates_AAAA-MM-DD.json --pick 3 # genera la #3
.venv/bin/python3 gen_cover.py --desc "<texto oferta>" --title T --company C  # sin scraping
```

**Dedup entre corridas:** `run_discover.py` salta URLs en `applied_urls.txt` (con
carta/postuladas) y en `output/seen_discovered.txt` (ya listadas antes) → cada
corrida muestra solo lo nuevo. `gen_cover.py` marca `applied` al generar.

**Import lazy de `cover`:** `run_discover.py`/`run_batch.py` solo importan el SDK
de IA (`anthropic`) con `--with-cover`. La PC de descubrimiento puede listar sin
tener `anthropic` instalado.

**Boards activos:**
- GetOnBrd        — ~18 cartas/corrida (LATAM, API JSON, remoto real)
- Himalayas       — ~11 cartas/corrida (global, API JSON, filtro Entry+Mid nativo)
- We Work Remotely — RSS público, ~27 candidatas, jobs de calidad worldwide
- 4 Day Week      — API JSON, remote+entry/mid, ~25 candidatas por corrida
- Remote First Jobs — API JSON, entry/middle/intern, ~168 candidatas por corrida
- Working Nomads  — API JSON, 2 categorías, ~3-5 cartas/corrida
- LinkedIn        — jobs-guest endpoint (sin login), ~28-56 crudas/corrida → ~10 candidatas; rate-limit agresivo (sleep 4s/página)
- Hacker News     — hilo mensual "Who is hiring" (API Algolia), ~150 crudas → ~28 candidatas; parseo heurístico
- Total tipico: 50-80 cartas/corrida (todos los boards)

**Filtros en cascada:**
1. Keywords tecnicas en titulo (`TECH_FILTER`)
2. Sin senior/lead/architect/ssr en titulo (`_SENIOR_EXCLUDE`)
3. Sin "3+ años de experiencia" en descripcion (`_EXP_EXCLUDE`)
4. [Himalayas] `worldwide=true` en API + exclusion por URL de país (`_HIMALAYAS_URL_COUNTRY`)
5. [WWR/4DW/RFJ/WN] `filter_global_remote` — excluye paises incompatibles con `CANDIDATE_REGION`, marca ambiguos con `[!]`

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
- `discover_linkedin(keywords, remote_only, max_pages)` — endpoint guest público `jobs-guest/jobs/api/seeMoreJobPostings/search` (SIN login); parsea tarjetas HTML (`base-card`); filtros nativos `f_WT=2` (remote) + `f_E=1,2` (Internship+Entry) + `f_TPR` (última semana); solo links `/jobs/view/` (evita duplicar con `/company/`); `description=""` (la scrapea el pipeline). OJO: rate-limit 429 → `sleep(4)` por página, `max_pages` bajo, headers realistas con `Accept-Language: en-US` obligatorio
- `discover_hackernews()` — API Algolia (sin anti-bot); busca hilo "Who is hiring" más reciente → trae `children` (cada comentario = una oferta) → parseo heurístico de la 1ª línea `Company | Role | Location | ...`; filtra por `remote` + `TECH_FILTER`; `description` = texto completo del comentario
- `discover_wellfound()` — Playwright headless=False + intercepción GraphQL; requiere `.wellfound_session.json`; DESHABILITADO por default (captcha frecuente + pocos resultados Ecuador)
- `filter_himalayas_location(jobs)` — passthrough (worldwide=true ya filtra en API)
- `discover_remotive()` — API JSON (actualmente limitada a ~28 jobs fijos en tier free)
- `discover_glovo(tech_only)` — Playwright en careers.glovoapp.com (0 resultados, pendiente fix)
- `filter_tech(jobs)` — keywords tecnicas en titulo
- `filter_junior(jobs)` — excluye senior/lead/ssr/etc en titulo
- `filter_entry_level(jobs)` — excluye si descripcion pide 3+ años
- `filter_global_remote(jobs)` — excluye ubicaciones incompatibles con `CANDIDATE_REGION`; agrega `location_warning` a los ambiguos
- `getonbrd_apply_url(url)` — retorna `{url}/applications/new`
- `resolve_apply_url(url)` — encuentra URL ATS externa via Playwright

## Current State (2026-06-16)

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
- Refactor (2026-06-12): eliminados todos los datos personales hardcodeados del repo. `cover.py`, `apply_ats.py` y `boards.py` ahora obtienen todo desde `.env`. Filtros geográficos configurables via `CANDIDATE_REGION` (LATAM/EUROPE/ASIA/USA/GLOBAL). Proyecto usable por cualquier candidato sin tocar el código fuente.
- Portafolio actualizado (2026-06-08): 5 proyectos nuevos en ES+EN — MotoVox (Flutter+C+WebRTC+FFI), Flores Eternas (Node.js+SRI Ecuador), Taller App (Node.js+React freelance), ApplyJob (Python+Playwright+AI), QR Shield (Python+Chrome Extension). GitHub links agregados a Centro Tia Glenda, EcuaInventario y Facturador.
- CV React (`lib/cv/content.ts`) actualizado (2026-06-08): bullet Flores Eternas en Freelance + MotoVox como 5to proyecto. PDFs ES/EN regenerados.
- GitHub limpiado (2026-06-08): READMEs y About descriptions en todos los repos publicos. TIER 1: TiaGlenda (prod), EcuaInventario, Facturador, SimuladorExamenes. TIER 2: MotoVox, TallerApp. TIER 3: qr-shield, mcp-context-server (3★), ApplyJob.
- Output files (gitignored): `output/sezzle_latam_answers.txt`, `output/monterail_pick_one_tool.txt`, `output/tritone_why.txt`, `output/tritone_why_en.txt`, `output/getonbrd_perfil_actualizado.txt`, `output/getonbrd_perfil_actualizado_en.txt`.
- Observacion del pipeline (2026-06-09): de 256 cartas generadas, la mayoria son senior/geo-restringidas (India, UK, US, LATAM especifico sin Ecuador). Los validos aplicados: Bluelight x3, Sezzle, Monterail, Tritone, EasyAudit AI, BC Tecnologia x3, Idealista, Designcafe. Pattern: Remote First Jobs genera muchos falsos positivos de seniority; revisar individualmente antes de postular.
- CV rehecho (2026-06-14): nuevo formato Harvard via python-docx. `profile/generate_cv.py` genera ES+EN .docx → convertir a PDF con LibreOffice. CVs en portafolio (`mickaell-portafolio/public/`) también actualizados. `CV_PATH`/`CV_PATH_EN` en .env apuntan a `cv_es.pdf`/`cv_en.pdf`.
- Sesion 2026-06-14: 11 postulaciones enviadas — Lazo, Ryz Labs, Linqia, Siena, vvd, POS+ (email), South Geeks, Espeo (6 semanas), Chief Rebel (email), Sticker Mule, Mindrift.
- Rechazos 2026-06-14: POS+ (Jordan Thaeler — "requires more experience"; vivió en Quito, recomendó Kushki para más adelante). Espeo (2026-06-16, otro candidato). Clerkie (2026-06-16, internship antiguo).
- Sezzle (2026-06-14): avanzó a Wonderlic assessment — completado. Resultado: Strong Problem-Solver + Highly Candid + Applied Work. Video proctoring: error en Google Form al subir, se reportó al equipo via formulario de contacto. **RECHAZADO 2026-06-19** (eligieron a otro candidato; mantienen CV en archivo para futuras vacantes).
- Para el futuro: **Kushki** (fintech Ecuador, recomendado por Jordan de POS+) — aplicar cuando haya más experiencia.
- Postulaciones activas al 2026-06-16: ~20 (Lazo, Ryz Labs, Linqia, Siena, vvd, South Geeks, Chief Rebel, Sticker Mule, Mindrift, Sezzle en proceso, + anteriores aún activas).
- Sesion 2026-06-21: revisado boletín JuniorJobs semanal — sin matches limpios para perfil Ecuador/junior/remoto-global (todo España-UE o LATAM country-locked sin Ecuador; las stack-fit eran Canonical, en cooldown hasta dic-2026). Sezzle RECHAZADO 2026-06-19 (tras Wonderlic). Postulaciones de esta semana aún pendientes de respuesta.
- Tech Holding Frontend Engineer WME (504): rechazado (2026-06-16) — llegó a entrevista AI pero no avanzó. Plataforma: Paradox/HireVue (AI interview). Candidato quiere practicar entrevistas AI antes de próximas rondas.
- Sesion 2026-06-22: 3 postulaciones enviadas — Hostinger (Full-Stack Node.js, WWR), TechBiz Global (Software Developer Security, RemoteFirstJobs), Quinncia Inc (Frontend Developer, Wellfound). TechBiz y Quinncia confirmadas mismo dia. Quinncia es la mejor: worldwide, full-time, huso EST (= Ecuador), $20-35k/anio. Respuestas guardadas en output/techbiz_answers.txt y output/quinncia_answers.txt.
- Rechazos 2026-06-22: Sweed (#20, AI Engineer) y Sticker Mule (#34, Software Engineer).
- Perfil Wellfound reconfigurado (2026-06-22): el candidato tenia Desired Salary en $500 (creyo que era mensual, el campo es ANUAL) — corregido a $24.000/anio. Cambiado a remote-only, bio/skills/preferencias actualizadas. Aprendizaje clave: un salario muy bajo descarta porque parece que el candidato no se valora. Textos en output/wellfound_profile.txt.
- PENDIENTE: grabar la AI interview de Wellfound (reutilizable, asincrona ~15 min, presenta al candidato PRIMERO a las empresas y se comparte en futuras aplicaciones). Ofrecer guia de prep STAR antes de grabarla.
- Boletin JuniorJobs (domingo) confirmado inutil para Ecuador-remoto: España/UE = exigen reubicacion/permiso UE (incluso roles "100% remoto" como Revolut Graduate 2027 que son hibridos con relocation a Poland/Portugal/Spain/UAE/UK + 3 dias oficina); LATAM = anclado a pais especifico (MX/CO/CL/AR/BR). Unico empleador global-remoto: Canonical (bloqueado hasta ~dic-2026 tras 4 rechazos + prohibe IA). NO correr el pipeline sobre las 256 ofertas (desperdicia API). Revolut Graduate 2027 (Python/Frontend): stack y timing encajan — reconsiderar SOLO si el candidato acepta reubicarse.
- Boards agregados (2026-06-25): **LinkedIn** (`discover_linkedin`, endpoint jobs-guest sin login) y **Hacker News** (`discover_hackernews`, hilo "Who is hiring" via API Algolia). Motivo: las fuentes previas se saturan de senior/geo-restringidos; el mejor match del finde (Unumbio) lo halló el candidato a mano en LinkedIn. Probados en seco: LinkedIn ~56 crudas→10 candidatas, HN ~152→28. Integrados en `run_discover.py` (tuple `only_board` + bloques discover con `filter_global_remote`). LinkedIn: cuidado 429 (sleep 4s/página). HN: parseo heurístico (campos imperfectos, revisar `[!]`). Postulación sigue MANUAL.
- Refactor de costo API (2026-06-25): una corrida del 23-jun gastó $0.19 generando carta para CADA candidata (~40) cuando solo se usan 1-3. Dos fixes: (A) `cover.py` reordenado para cache de prefijo de DeepSeek (constante primero, oferta al final) → ~80-90% menos input; verificado `cache_read=896` en la otra PC. (B) **desacople descubrir↔generar**: `run_discover.py` y `run_batch.py` por defecto solo LISTAN (0 API) y vuelcan `candidates_*.json`; cartas opt-in con `--with-cover`. Nuevo `gen_cover.py` genera UNA carta on-demand (`<url>`/`--desc`/`--from-json --pick`). Nuevo `src/applied.py` (tracking compartido: `applied_urls.txt` + `output/seen_discovered.txt`). Import de `cover` lazy → listar no requiere `anthropic`. `run_manual.py` NO se tocó (ahí generar es el punto). Verificado en seco: HN lista 22 candidatas, 0 API, 0 cartas. PENDIENTE confirmar `cache_read` en vivo en la PC con `anthropic`.

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
- LinkedIn jobs-guest: cada tarjeta trae 2 links (`/jobs/view/` el real + `/company/` el del logo). Filtrar solo `/jobs/view/` o se duplica cada oferta. El rate-limit 429 es agresivo: ir lento (`sleep 4s`/página, `max_pages` 2-3) y `Accept-Language: en-US` obligatorio o bloquea.
- Hacker News "Who is hiring": parseo heurístico de la 1ª línea del comentario (`Company | Role | Location | ...`); como el formato es libre, algunos `role`/`location` salen cruzados — `filter_junior`/`filter_role_noise` limpian downstream, pero revisar los `[!]` antes de postular.
