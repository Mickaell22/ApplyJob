#!/usr/bin/env python3
"""Procesa el boletín de JuniorJobs desde texto plano.

Parsea automáticamente los links, filtra jobs con bandera de país,
aplica los mismos filtros que cli/run_discover.py y genera cartas.

Uso:
  python cli/run_batch.py boletin.txt        # desde archivo (solo lista, 0 API)
  cat boletin.txt | python cli/run_batch.py  # desde stdin (pipe)
  python cli/run_batch.py                    # pegar texto + Ctrl+D para terminar
  python cli/run_batch.py boletin.txt --with-cover   # ademas genera cartas (gasta API)
"""

import re
import sys
import os
import json
import datetime
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# cover (DeepSeek/anthropic) se importa lazy mas abajo, solo con --with-cover.
from src import profile, matcher, boards
from src.scraper import fetch_job

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "cartas")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Parser del boletín
# ---------------------------------------------------------------------------

# Emoji de bandera = dos Regional Indicator letters juntas (🇦🇷🇧🇷🇨🇴🇲🇽🇬🇧etc.)
_FLAG_RE = re.compile(r"[\U0001F1E0-\U0001F1FF]{2}")
_URL_RE  = re.compile(r"https?://\S+")

# Verbos típicos del boletín de JuniorJobs
_VERB_RE = re.compile(
    r"\s+(?:necesita a un|necesita un|busca a un|buscando a un|busca un|"
    r"tiene disponible su|is looking for a?|seeks? a?)\s+",
    re.IGNORECASE,
)

# Emojis que NO son banderas (🚨🧑‍💻⚡ etc.) — limpiar antes de parsear empresa/título
# Flags = U+1F1E0-U+1F1FF (Regional Indicators); los excluimos del match.
_NON_FLAG_EMOJI_RE = re.compile(
    r"[\U00002600-\U000027BF"      # misc symbols / dingbats (☀✅⚡)
    r"\U0001F300-\U0001FAFF"       # emoji principales (🚨🧑💻) — NO incluye flags (1F1E0-1F1FF)
    r"\U0000200D\U0000FE0F]+"      # ZWJ + variation selector
)


def parse_boletin(text: str) -> list[dict]:
    """Extrae jobs del texto del boletín JuniorJobs.

    Formato típico:
      N. Empresa necesita a un Título: https://...
      N. 🇬🇧 Empresa busca un Título: https://...
      N. 🚨 Empresa busca a un Título: https://...
    """
    jobs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        url_m = _URL_RE.search(line)
        if not url_m:
            continue

        url      = url_m.group().rstrip(".,)")
        has_flag = bool(_FLAG_RE.search(line))

        # Texto antes de la URL
        before = line[: url_m.start()].strip().rstrip(":").strip()
        before = re.sub(r"^\d+\.\s*", "", before)           # quitar "13. "
        before = _FLAG_RE.sub("", before).strip()            # quitar banderas 🇬🇧
        before = _NON_FLAG_EMOJI_RE.sub("", before).strip()  # quitar 🚨🧑‍💻 etc.
        # Prefijos narrativos de JuniorJobs: "Sigue con las activas X", "También está X"
        before = re.sub(
            r"^(?:sigue con las activas?|también está?|continúa?|novedades con)\s+",
            "", before, flags=re.IGNORECASE,
        ).strip()

        # Separar empresa y título por el verbo
        verb_m = _VERB_RE.search(before)
        if verb_m:
            company = before[: verb_m.start()].strip()
            title   = before[verb_m.end() :].strip()
        else:
            company = ""
            title   = before

        jobs.append({
            "title":        title or before,
            "company":      company,
            "url":          url,
            "source":       "juniorjobs",
            "country_flag": has_flag,
            "remote":       None,
            "description":  "",
        })

    return jobs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print("=" * 64)
    print("BOLETIN JUNIORJOBS — Procesador automático")
    print("=" * 64)

    # Por defecto solo lista candidatas (0 API). --with-cover genera cartas.
    with_cover = "--with-cover" in sys.argv
    if with_cover:
        from src import cover  # import lazy: anthropic solo si se piden cartas
    filepath = next((a for a in sys.argv[1:] if not a.startswith("--")), None)

    if filepath:
        with open(filepath, encoding="utf-8") as f:
            raw_text = f.read()
        print(f"Leyendo: {filepath}")
    elif not sys.stdin.isatty():
        raw_text = sys.stdin.read()
        print("Leyendo desde stdin...")
    else:
        print("Pegá el texto del boletín y presioná Ctrl+D cuando termines:\n")
        raw_text = sys.stdin.read()

    # -----------------------------------------------------------------------
    # Parsear y pre-filtrar
    # -----------------------------------------------------------------------

    all_jobs = parse_boletin(raw_text)
    print(f"\n{len(all_jobs)} links encontrados en el boletín")

    flagged     = [j for j in all_jobs if j["country_flag"]]
    no_flag     = [j for j in all_jobs if not j["country_flag"]]
    tech_jobs   = boards.filter_tech(no_flag)
    junior_jobs = boards.filter_junior(tech_jobs)

    print(f"  {len(flagged)} con bandera de país → descartados automáticamente")
    if flagged:
        for j in flagged:
            print(f"    ✗ {j['company']:20} {j['title']}")
    print(f"  {len(no_flag)} sin bandera → {len(tech_jobs)} técnicas → {len(junior_jobs)} sin senior/lead\n")

    if not junior_jobs:
        print("[!] Ninguna oferta pasó los filtros.")
        sys.exit(0)

    # -----------------------------------------------------------------------
    # CV
    # -----------------------------------------------------------------------

    cv = profile.load()
    if "error" in cv:
        print(f"[!] Error cargando CV: {cv['error']}")
        sys.exit(1)
    print(f"CV cargado: {len(cv.get('techs', []))} tecnologías\n")

    # -----------------------------------------------------------------------
    # Pipeline: resolver URL → scrape → filtro exp → match → carta
    # -----------------------------------------------------------------------

    results = []

    for job in junior_jobs:
        print("=" * 64)
        print(f"[JUNIORJOBS] {job['title']}")
        company_str = f"@ {job['company']}" if job["company"] else ""
        print(f"  {company_str}  →  {job['url']}")

        # Resolver short URL
        print("  Resolviendo short URL...")
        try:
            r = httpx.head(job["url"], follow_redirects=True, timeout=10)
            real_url = str(r.url)
            job["url"] = real_url
            print(f"  → {real_url[:80]}")
        except Exception as e:
            print(f"  [!] No se pudo resolver: {e} — usando URL original")

        # Scrapear descripción
        print("  Scrapeando descripción...")
        detail = fetch_job(job["url"])
        if "error" in detail:
            print(f"  [!] Scraping fallido: {detail['error']}")
            continue
        job["description"] = detail.get("description", "")
        if not job.get("company") and detail.get("company"):
            job["company"] = detail["company"]
        if not job["description"]:
            print("  [!] Sin descripción — omitida")
            continue

        # Filtro de experiencia (3+ años)
        if not boards.filter_entry_level([job]):
            print("  [x] Requiere 3+ años de experiencia — omitida")
            continue

        # Verificar si es remoto (advertencia, no descarta)
        if job["remote"] is None:
            job["remote"] = bool(boards.REMOTE_FILTER.search(job["description"]))
        if not job["remote"]:
            print("  [!] No menciona remoto — verificar antes de postular")

        # Match contra CV
        match = matcher.score(job, cv)
        print(f"  Match: {match['score']}% ({match['fit']}) — techs: {match['matched_techs'][:6]}")
        if match["fit"] == "baja":
            print("  [x] Compatibilidad baja — omitida")
            continue

        # Generar carta SOLO con --with-cover (cuesta API). Default: solo listar.
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
                company_slug = re.sub(r"[^a-z0-9]+", "_", (job["company"] or "empresa").lower())[:20]
                title_slug   = re.sub(r"[^a-z0-9]+", "_", job["title"].lower())[:30]
                slug         = f"boletin_{company_slug}_{title_slug}".strip("_")
                out_path     = os.path.join(OUT_DIR, f"{slug}.txt")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(carta)
                print(f"  Carta guardada: output/cartas/{slug}.txt")
        else:
            print("  [+] Candidata listada (sin carta — cli/gen_cover.py para generar)")

        results.append({"job": job, "match": match, "carta": carta, "path": out_path})

    # -----------------------------------------------------------------------
    # Resumen
    # -----------------------------------------------------------------------

    if results:
        cand_path = os.path.join(OUT_DIR, f"candidates_boletin_{datetime.date.today()}.json")
        with open(cand_path, "w", encoding="utf-8") as f:
            json.dump(
                [{"url": r["job"]["url"], "title": r["job"]["title"],
                  "company": r["job"].get("company", ""),
                  "source": "juniorjobs",
                  "location": r["job"].get("location_required", ""),
                  "match": r["match"]["score"],
                  "description": r["job"].get("description", "")[:3000]}
                 for r in results],
                f, ensure_ascii=False, indent=2,
            )
        print(f"\nCandidatos guardados: {cand_path}")
        print(f"  Generá carta on-demand: python cli/gen_cover.py --from-json {cand_path} --pick <n>")

    print("\n" + "=" * 64)
    _kind = "cartas generadas" if with_cover else "candidatas listadas"
    print(f"RESUMEN: {len(results)} {_kind} de {len(junior_jobs)} candidatas")
    print()

    if results:
        results.sort(key=lambda r: r["match"]["score"], reverse=True)
        for i, r in enumerate(results, 1):
            j    = r["job"]
            comp = j.get("company") or "?"
            rem  = "REMOTO" if j.get("remote") else "[verificar remoto]"
            print(
                f"  {i}. [{r['match']['score']:3}%] {comp:20} {j['title'][:40]}"
                f"  {rem}"
            )
            print(f"       {j['url'][:75]}")
        print()
        best = results[0]
        print(f"★ Mejor match: {best['job']['title']} @ {best['job'].get('company', '?')} ({best['match']['score']}%)")
