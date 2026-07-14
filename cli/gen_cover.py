#!/usr/bin/env python3
"""Genera UNA carta on-demand tras revisar el link manualmente.

Solo gasta API DeepSeek para la oferta que decidís postular (no para las ~40
candidatas). Complementa a run_discover.py, que ahora solo lista (0 API).

Uso:
  python gen_cover.py <url> [--lang en]                         # scrapea la URL
  python gen_cover.py --desc "<texto>" --title T --company C [--lang en]
  python gen_cover.py --from-json output/cartas/candidates_AAAA-MM-DD.json
                                                                 # lista para elegir
  python gen_cover.py --from-json <archivo.json> --pick <n|url> [--lang en]

Antes de generar corre una evaluacion (src/evaluator.py): reglas duras 0 API
(senior, 3+ años, prohibe IA, pais incompatible) y si pasan, DeepSeek puntua
CV vs oferta y decide Apply/Consider/Research/Skip. Con Skip no se genera
carta (--force para forzar; --no-eval para saltar la evaluacion).
"""
import sys
import os
import re
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# cover (DeepSeek/anthropic) se importa lazy justo antes de generar, asi listar
# el JSON de candidatos (--from-json sin --pick) no requiere anthropic.
from src import profile, applied
from src.scraper import fetch_job

ap = argparse.ArgumentParser()
ap.add_argument("url", nargs="?")
ap.add_argument("--desc")
ap.add_argument("--title", default="")
ap.add_argument("--company", default="")
ap.add_argument("--from-json", dest="from_json")
ap.add_argument("--pick", help="indice (0-based) o URL dentro del JSON de candidatos")
ap.add_argument("--lang", default="es")
ap.add_argument("--no-eval", action="store_true",
                help="saltar la evaluacion previa (reglas duras + DeepSeek)")
ap.add_argument("--force", action="store_true",
                help="generar la carta aunque la evaluacion diga Skip")
a = ap.parse_args()

if a.from_json:
    with open(a.from_json, encoding="utf-8") as f:
        cands = json.load(f)
    if a.pick is None:
        for i, c in enumerate(cands):
            comp = str(c.get("company") or "?")[:22]
            print(f"  [{i:3}] {str(c.get('match', '?')):>3}%  {comp:22} | {c.get('title', '')[:45]}")
        sys.exit("\nElegí con --pick <n|url>")
    if a.pick.isdigit():
        c = cands[int(a.pick)]
    else:
        c = next((x for x in cands if x.get("url") == a.pick), None)
        if not c:
            sys.exit(f"no encontré la URL {a.pick} en {a.from_json}")
    job = {"title": c.get("title", ""), "company": c.get("company", ""),
           "description": c.get("description", ""), "url": c.get("url", ""),
           "location_required": c.get("location", ""),
           "canal": c.get("canal", "remoto")}
elif a.desc:
    job = {"title": a.title, "company": a.company, "description": a.desc, "url": ""}
elif a.url:
    d = fetch_job(a.url)
    if "error" in d:
        sys.exit(f"scraping fallido: {d['error']}")
    job = {"title": a.title or d.get("title", ""),
           "company": a.company or d.get("company", ""),
           "description": d.get("description", ""), "url": a.url}
else:
    sys.exit("pasá una <url>, --desc, o --from-json")

if not job.get("description"):
    sys.exit("sin descripción — no se puede generar una carta útil")

cv = profile.load()
if "error" in cv:
    sys.exit(f"error cargando CV: {cv['error']}")

# Evaluacion previa: reglas duras (0 API) y, si pasan, DeepSeek razona CV vs
# oferta. Solo aca — nunca sobre el batch de descubrimiento.
if not a.no_eval:
    from src import evaluator
    ev = evaluator.evaluate_with_overrides(job, cv)
    print(f"Evaluacion: {ev.get('decision')}"
          + (f"  (promedio {ev['promedio']}/5)" if ev.get("promedio") is not None else ""))
    for k in ("match_cv", "nivel_fit", "remoto_real", "comp", "global"):
        if ev.get(k) is not None:
            print(f"  {k:12}: {ev[k]}")
    if ev.get("red_flags"):
        print("  red flags  : " + "; ".join(str(f) for f in ev["red_flags"]))
    if ev.get("threshold_warning"):
        print(f"  [!] {ev['threshold_warning']}")
    if ev.get("razon"):
        print(f"  razon      : {ev['razon']}")
    if ev.get("decision") == "Skip" and not a.force:
        sys.exit("decision=Skip — no genero carta (usa --force para generar igual)")

from src import cover  # import lazy: anthropic solo al momento de generar
carta = cover.generate(job, cv, lang=a.lang)
slug = re.sub(r"[^a-z0-9]+", "_", (job.get("company") or job.get("title") or "carta").lower())[:50].strip("_")
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "cartas", f"manual_{slug}.txt")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write(carta)

# Marcar como postulada para que descubrir no la vuelva a listar
if job.get("url"):
    applied.mark_applied(job["url"])

print(carta + f"\n\n--> guardada en {out}")
