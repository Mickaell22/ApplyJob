#!/usr/bin/env python3
"""
ApplyJob — Automatizacion de postulaciones laborales.

Modo CLI:
    python main.py <url1> <url2> ...
    echo "url1 url2" | python main.py

Modo integracion (desde el agente):
    from src import scraper, profile, matcher, cover, sender
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from src import scraper, profile, matcher, cover, sender


def run(urls: list[str]) -> list[dict]:
    """Pipeline completo: scrape -> match -> cover -> send."""
    print(f"[ApplyJob] Procesando {len(urls)} ofertas...\n")

    cv = profile.load()
    if "error" in cv:
        print(f"[!] {cv['error']}")
        return []

    results = []
    for job in scraper.fetch_all(urls):
        print(f"---\n[+] {job.get('title', '?')} en {job.get('company', '?')}")
        print(f"    URL: {job['url']}")

        if "error" in job:
            print(f"    [!] Error: {job['error']}")
            results.append(job)
            continue

        match = matcher.score(job, cv)
        print(f"    Compatibilidad: {match['score']}% ({match['fit']})")

        if match["fit"] in ("baja",):
            print(f"    [x] Descartada, baja compatibilidad")
            job["skipped"] = True
            results.append(job)
            continue

        print(f"    Generando carta personalizada...")
        carta = cover.generate(job, cv)
        email = cv.get("email") or os.getenv("GMAIL_USER")

        # Buscar email de la empresa desde la oferta (placeholder)
        empresa_email = _guess_hr_email(job)

        if empresa_email and email:
            result = sender.send(
                to_email=empresa_email,
                subject=f"Candidatura: {job.get('title', '')}",
                body=carta,
                attachment=os.getenv("CV_PATH", "profile/cv.md"),
            )
            if result.get("ok"):
                print(f"    [v] Enviado a {empresa_email}")
            else:
                print(f"    [!] Error al enviar: {result.get('error')}")
        else:
            print(f"    [~] Sin email destino. Carta lista:\n{carta[:200]}...")

        results.append(job)

    return results


def _guess_hr_email(job: dict) -> str | None:
    """Intenta extraer email de contacto de la oferta."""
    import re
    text = job.get("description", "")
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    # Filtrar correos comunes de RRHH
    for e in emails:
        if any(k in e.lower() for k in ("hr", "talent", "jobs", "career", "apply", "trabajo")):
            return e
    return emails[0] if emails else None


def main():
    urls = sys.argv[1:] or sys.stdin.read().strip().split()
    if not urls:
        print("Uso: python main.py <url1> <url2> ...")
        sys.exit(1)
    run(urls)


if __name__ == "__main__":
    main()
