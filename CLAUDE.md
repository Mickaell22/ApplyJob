# CLAUDE.md — ApplyJob Project Context

## Overview

ApplyJob automatiza postulaciones laborales. Pipeline: extraer ofertas → matchear contra perfil → generar cover letter con DeepSeek → postular en ATS via Playwright.

## Key Files

- `main.py` — orquestador CLI del pipeline clasico (scrape → match → cover → send)
- `src/scraper.py` — extrae info de ofertas desde URLs (httpx + Playwright fallback)
- `src/matcher.py` — calcula % de compatibilidad oferta vs perfil
- `src/cover.py` — genera carta personalizada con DeepSeek Flash (via Anthropic SDK)
- `src/apply_ats.py` — auto-postulacion en ATS con Playwright (Workable funcional); soporta `lang="en"` para subir CV EN
- `src/letter_to_pdf.py` — convierte cartas .txt a PDF via python-docx + LibreOffice
- `src/sender.py` — envia carta por Gmail SMTP
- `src/inbox.py` — lector IMAP para boletines de ofertas
- `run_batch.py` — batch: resuelve short URLs, scrapea con Playwright y genera cartas
- `run_manual.py` — batch con descripciones manuales (cuando el scraping falla)
- `run_today.py` — genera cartas para la shortlist de ofertas de la fecha actual
- `profile/cv.md` — perfil del candidato en español (stack, experiencia, skills)
- `profile/cv_en.md` — perfil del candidato en INGLES (para ofertas en ingles, ej. Canonical)
- `profile/CV_Mickaell_Moran.pdf` — CV en PDF (español)
- `profile/CV_Mickaell_Moran_EN.pdf` — CV en PDF (ingles, para Canonical y ofertas EN)
- `output/cartas/` — cartas generadas (GITIGNORED: contienen datos de contacto reales/PII)
- `output/canonical_form_answers.txt` — respuestas reutilizables para formularios Canonical (GITIGNORED)
- `samples/` — boletines de ofertas guardados

## ATS Auto-Apply Module (`src/apply_ats.py`)

Usa Playwright headless Chromium para llenar formularios de postulacion.

**Plataformas soportadas:**
- Workable ✅ — Platzi, Canonical, Loft
- Greenhouse ✅ — Canonical (handler completo; pendiente test real)
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
```

## Current State (2026-06-01)

- CV bilingüe completo: `profile/cv.md` (ES) + `profile/cv_en.md` (EN) + PDFs en ambos idiomas.
- `cover.generate` soporta `lang="es"/"en"`. `apply_ats.run()` soporta `lang="en"` para subir CV EN.
- `src/letter_to_pdf.py` — genera PDFs de cartas desde .txt via python-docx + LibreOffice.
- Postulaciones enviadas (boletin 2026-05-31): Canonical x4 EN (07,12,13,14 — manuales, Canonical prohibe IA) + Addi CyberSec (11). Confirmacion Greenhouse recibida para las 4 de Canonical.
- `output/canonical_form_answers.txt` — respuestas reutilizables para proximas aplicaciones Canonical (gitignored, en disco).
- Restriccion del candidato: SOLO remoto-real (estudiante en Guayaquil, sin reubicacion). Canonical = mejor caja (remoto global, junior/graduate, Python/Linux).
- To-do: arreglar handler Teamtailor (roto), agregar Ashby (Addi), seguimiento proceso Canonical (written interview + Devskiller), test real Greenhouse con oferta Canonical.

## Common Issues

- Scraper falla con short URLs (juniorjobs.short.gy) porque redirigen a JS-heavy ATS
- Solucion: resolver short URLs con httpx.head() primero, luego scrapear URL final con Playwright
- Matcher da scores bajos si la descripcion extraida no contiene keywords tecnicas
- Teamtailor tiene cookie wall que bloquea contenido → `apply_teamtailor` da Timeout/no encuentra boton (probado 2026-05-31, sigue roto)
- Workable requiere manejar firstname/lastname separados
- Muchas ofertas "100% remoto" son remoto DENTRO del pais (ej. Loft Brasil = CLT + portugués); verificar antes de aplicar
- Workday/Oracle exigen crear cuenta con login + verificación email → no automatizables de forma confiable
