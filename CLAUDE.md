# CLAUDE.md — ApplyJob Project Context

## Overview

ApplyJob automatiza postulaciones laborales. Pipeline: extraer ofertas → matchear contra perfil → generar cover letter con DeepSeek → postular en ATS via Playwright.

## Key Files

- `main.py` — orquestador CLI del pipeline clasico (scrape → match → cover → send)
- `src/scraper.py` — extrae info de ofertas desde URLs (httpx + Playwright fallback)
- `src/matcher.py` — calcula % de compatibilidad oferta vs perfil
- `src/cover.py` — genera carta personalizada con DeepSeek Flash (via Anthropic SDK)
- `src/apply_ats.py` — auto-postulacion en ATS con Playwright (Workable funcional)
- `src/sender.py` — envia carta por Gmail SMTP
- `src/inbox.py` — lector IMAP para boletines de ofertas
- `profile/cv.md` — perfil del candidato (stack, experiencia, skills)
- `profile/CV_Mickaell_Moran.pdf` — CV en PDF para adjuntar
- `output/cartas/` — cartas de presentacion generadas
- `samples/` — boletines de ofertas guardados

## ATS Auto-Apply Module (`src/apply_ats.py`)

Usa Playwright headless Chromium para llenar formularios de postulacion.

**Plataformas soportadas:**
- Workable ✅ — Platzi, Canonical, Loft
- Teamtailor 🔧 — Global66, Buk (en desarrollo)
- Ashby 📋 — Addi (pendiente)
- Workday 📋 — Amadeus, Oracle (pendiente)

**Funcionamiento:**
1. Navega a la URL de la oferta
2. Acepta cookies
3. Busca y clickea boton "Apply"
4. Llena campos (nombre, email, telefono, ubicacion, linkedin)
5. Sube CV en PDF
6. Pega cover letter en textarea
7. Click submit (dry_run=True para probar sin enviar)

**Modo dry_run:** `run(jobs_with_letters, dry_run=True)` — llena formulario pero NO hace submit.

**Candidate data:** Se carga desde `.env` (GMAIL_USER) + constantes en `CANDIDATE` dict.

## CV / Profile

El perfil esta en `profile/cv.md`. Se extraen tecnologias via regex de las secciones "Stack" y "Skills".

**Techs extraidos:** python, django, fastapi, react, typescript, node.js, flutter, dart, postgresql, docker, linux, git, firebase, rest, api, y mas (25 total).

## Matcher

`matcher.score(job, cv)` → compara tech keywords contra titulo+descripcion de la oferta.
- Score = (keywords matcheados / total keywords) * 100
- >40% = alta, 20-40% = media, <20% = baja (descartada)

## Cover Letter Generation

`cover.generate(job, cv)` → usa DeepSeek Flash via Anthropic SDK.
- Prompt incluye: titulo oferta, empresa, descripcion, datos del candidato, perfil completo
- Output: carta profesional en español, sin emojis, <250 palabras, con datos de contacto reales

## .env Required

```
DEEPSEEK_API_KEY=sk-...
GMAIL_USER=tu-correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
CV_PATH=./profile/CV_Mickaell_Moran.pdf

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

## Current State (May 2026)

- Branch `fix/audit-logging-tests` tiene mejoras (logging estructurado, tests) sin mergear a main
- CV ya completado con stack real de Mickaell
- 5 cover letters generadas para ofertas Colombia/LATAM
- Apply ATS funcional para Workable (probado con Platzi)
- To-do: Teamtailor support, Ashby support, Workday support, LinkedIn field detection

## Common Issues

- Scraper falla con short URLs (juniorjobs.short.gy) porque redirigen a JS-heavy ATS
- Solucion: resolver short URLs con httpx.head() primero, luego scrapear URL final con Playwright
- Matcher da scores bajos si la descripcion extraida no contiene keywords tecnicas
- Teamtailor tiene cookie wall que bloquea contenido
- Workable requiere manejar firstname/lastname separados
