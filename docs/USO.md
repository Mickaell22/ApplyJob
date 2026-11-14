# Uso

[Volver al README](../README.md)

## Descubrir y generar cartas

`cli/run_discover.py` descubre ofertas de múltiples tableros, las filtra y **lista las
candidatas sin gastar API** (vuelca un JSON). Tú revisas los links y generas la
carta solo para la que vas a postular, con `cli/gen_cover.py`. Esto evita generar ~40
cartas por corrida cuando solo usas 1-3.

```bash
# 1) Descubrir y listar (0 API)
python cli/run_discover.py --no-apply          # todos los boards
python cli/run_discover.py getonbrd            # un board específico:
python cli/run_discover.py himalayas           #   getonbrd | himalayas | weworkremotely
python cli/run_discover.py weworkremotely      #   4dayweek | remotefirstjobs | workingnomads
python cli/run_discover.py 4dayweek            #   linkedin | hackernews
python cli/run_discover.py remotefirstjobs
python cli/run_discover.py workingnomads
python cli/run_discover.py linkedin
python cli/run_discover.py hackernews
python cli/run_discover.py linkedin-local      # canal LOCAL: LinkedIn en el pais del
                                           #   candidato (CANDIDATE_COUNTRY)
python cli/run_discover.py computrabajo        # canal LOCAL: Computrabajo (COMPUTRABAJO_DOMAIN)
python cli/run_discover.py multitrabajos       # canal LOCAL: Multitrabajos Ecuador (Playwright)
python cli/run_discover.py local               # los 3 boards del canal local juntos
python cli/run_discover.py --verify            # descartar ofertas expiradas (request extra c/u)
python cli/run_discover.py --with-cover        # (opt-in) además genera cartas — gasta API

# 2) Generar carta on-demand tras revisar el link (lo único que gasta API)
python cli/gen_cover.py https://url-de-la-oferta                       # scrapea la URL
python cli/gen_cover.py --from-json output/cartas/candidates_AAAA-MM-DD.json           # lista para elegir
python cli/gen_cover.py --from-json output/cartas/candidates_AAAA-MM-DD.json --pick 3  # genera la #3
python cli/gen_cover.py --desc "<texto de la oferta>" --title T --company C  # sin scraping
```

Antes de generar, `cli/gen_cover.py` evalúa la oferta (`src/evaluator.py`): reglas
duras sin API (título senior, "3+ años", prohíbe IA, país incompatible) y, si
pasan, DeepSeek puntúa CV vs oferta (match, nivel, remoto, comp, global) y
decide `Apply/Consider/Research/Skip`. Con `Skip` no se genera carta
(`--force` para forzar, `--no-eval` para saltarla).

**Boards soportados:**

| Board | Fuente | Filtro seniority |
|---|---|---|
| GetOnBrd | API JSON | Excluye Senior/Lead por ID |
| Himalayas | API JSON | Entry-level + Mid-level nativo |
| We Work Remotely | RSS XML | Manual (título) |
| 4 Day Week | API JSON | `level=entry,mid` en API |
| Remote First Jobs | API JSON | `entry_level/middle/intern` |
| Working Nomads | API JSON | Manual (título) |
| LinkedIn | HTML (jobs-guest, sin login) | `f_E=1,2` (Internship+Entry) en endpoint |
| LinkedIn (sesión) | Playwright + storage_state | `f_E=1,2`; requiere `scripts/setup_linkedin_session.py` |
| Hacker News | API Algolia (Who is hiring) | Manual (título) |
| LinkedIn LOCAL | HTML (jobs-guest, sin login) | `f_E=1,2`; busca en `CANDIDATE_COUNTRY`, acepta presencial/híbrido (`canal: local`) |
| Computrabajo | HTML server-rendered | Manual (título + "3+ años"); `canal: local`, subdominio via `COMPUTRABAJO_DOMAIN` |
| Multitrabajos | Playwright (SPA Bumeran, Ecuador) | Manual (título + "3+ años"); `canal: local` |

**Filtros en cascada:**
1. Keywords técnicas en título (`TECH_FILTER`)
2. Excluye senior/lead/architect en título
3. Excluye descripciones con "3+ años de experiencia"
4. `filter_global_remote` — excluye restricciones geográficas incompatibles con `CANDIDATE_REGION`

**Jobs marcados con `[!]`** en location son ambiguos (ciudad en lugar de país) — revisar antes de postular.

## Compatibilidad (matcher)

`matcher.score()` extrae las tecnologias de las secciones `Stack`/`Skills` de tu `cv.md` y
las busca en el titulo + descripcion de la oferta, con limite de palabra (sin el, `java`
matchea `javascript` y `ci` matchea `efficient`). El `fit` va por **cantidad** de
coincidencias, no por porcentaje:

- **Alta** (>=6 coincidencias): claramente de tu stack
- **Media** (>=2): senal suficiente para revisarla
- **Baja** (<2): descartada

El porcentaje se reporta pero es solo informativo: como el denominador es tu CV entero,
ampliar tu stack bajaria el porcentaje de la misma oferta y descalibraria el umbral solo.

Self-check: `.venv/bin/python3 tests/test_matcher.py`

## Pipeline completo (batch)

```bash
# Scrapea + match + genera cartas desde URLs reales
python cli/run_batch.py

# Usa descripciones manuales (cuando el scraping falla)
python cli/run_manual.py

# Genera cartas para la shortlist de ofertas de la fecha actual
python cli/run_today.py
```

Las cartas en ingles se generan con `cover.generate(job, cv, lang="en")` (ej. Canonical).

## Generar PDF de una carta

```bash
python src/letter_to_pdf.py output/cartas/07_Canonical_SWE_Python_Cloud.txt
# genera output/cartas/07_Canonical_SWE_Python_Cloud.pdf
```

## CLI directo

```bash
# Una oferta
python cli/main.py https://juniorjobs.short.gy/LbO1f3

# Varias ofertas
python cli/main.py https://juniorjobs.short.gy/LbO1f3 https://juniorjobs.short.gy/gjno2F

# Desde stdin
echo "url1 url2" | python cli/main.py
```

## Integracion desde codigo

```python
from src import profile, scraper, matcher, cover, sender

cv = profile.load()
job = scraper.fetch_job("https://juniorjobs.short.gy/LbO1f3")
match = matcher.score(job, cv)

if match["fit"] in ("alta", "media"):
    carta = cover.generate(job, cv)
    sender.send(
        to_email="hr@empresa.com",
        subject=f"Candidatura: {job['title']}",
        body=carta,
        attachment="./profile/cv_es.pdf",
    )
```

## Estructura del repo
```
ApplyJob/
├── cli/run_discover.py      # descubre boards → filtra → puntua → lista candidatas (0 API)
├── cli/gen_cover.py         # genera UNA carta on-demand para la oferta elegida
├── cli/main.py              # orquestador del pipeline clasico (una o varias URLs)
├── cli/run_batch.py         # batch: scrapea y lista desde URLs
├── cli/run_manual.py        # batch: usa descripciones manuales (cuando scraping falla)
├── cli/run_today.py         # genera cartas para la shortlist del dia
├── profile/
│   ├── cv.md            # perfil del candidato (lo leen matcher, cover y evaluator)
│   ├── cv_es.pdf        # CV en PDF (español)      ← CV_PATH en .env
│   ├── cv_en.pdf        # CV en PDF (ingles)        ← CV_PATH_EN en .env
│   ├── generate_cv.py   # genera los .docx del CV (fuente; los PDF son derivados)
│   └── cv_template.md   # plantilla de perfil para nuevos usuarios
├── src/
│   ├── boards/          # 13 fuentes de ofertas (paquete: _common, remote_global,
│   │                    #   linkedin, local, apply_urls)
│   ├── scraper.py       # extrae informacion de ofertas desde URLs
│   ├── matcher.py       # calcula compatibilidad oferta vs perfil
│   ├── evaluator.py     # evaluacion on-demand: reglas duras 0 API + puntaje LLM
│   ├── applied.py       # tracking de URLs ya vistas / ya postuladas
│   ├── cover.py         # genera carta via DeepSeek (es/en); datos 100% desde .env
│   ├── apply_ats.py     # relleno asistido de formularios ATS (opt-in, ver abajo)
│   ├── letter_to_pdf.py # convierte cartas .txt a PDF via python-docx + LibreOffice
│   ├── inbox.py         # lector IMAP para boletines
│   └── sender.py        # envia correo via Gmail SMTP
├── samples/             # boletines de ofertas guardados
├── output/
│   └── cartas/          # cartas generadas (gitignored: contienen PII)
└── .env                 # variables de entorno (no versionado)
```
