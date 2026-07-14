#!/usr/bin/env python3
"""Genera cartas para las ofertas remotas de esta fecha (boletin 2026-05-31).
Shortlist filtrada para perfil junior/primer empleo con stack Python/fullstack.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from src import profile, matcher, cover

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "cartas")
os.makedirs(OUT_DIR, exist_ok=True)

# Shortlist remota / junior-friendly del boletin de esta fecha.
# Descripciones redactadas a partir de empresa + rol + stack publico conocido.
jobs = [
    {
        "slug": "06_Global66_Backend_Developer",
        "title": "Backend Developer",
        "company": "Global66 Colombia",
        "url": "https://global66.teamtailor.com/jobs/7799854-backend-developer",
        "platform": "teamtailor",
        "description": (
            "Backend Developer en Global66, fintech de transferencias internacionales y "
            "cuenta global para LATAM. Stack backend con Python, APIs REST, microservicios, "
            "PostgreSQL y Docker en entornos cloud. Trabajo en el core de pagos que mueve "
            "dinero entre paises en tiempo real. Buscan perfiles con bases solidas en "
            "desarrollo backend, diseno de APIs, bases de datos relacionales y buenas "
            "practicas de codigo. Modalidad hibrida/remota en Colombia, Chile o Argentina."
        ),
    },
    {
        "slug": "07_Canonical_SWE_Python_Cloud",
        "title": "Software Engineer - Python - Cloud (graduate level)",
        "company": "Canonical (Ubuntu)",
        "url": "https://canonical.com/careers/3257589",
        "platform": "canonical",
        "description": (
            "Software Engineer enfocado en Python y Cloud, nivel graduate (early career), "
            "100% remoto global en Canonical, la empresa detras de Ubuntu Linux. Stack: "
            "Python, Linux, sistemas distribuidos, herramientas de infraestructura y cloud "
            "open source. Ideal para recien graduados o estudiantes avanzados con fuerte "
            "base en Python y Linux, capacidad de aprendizaje y pasion por el open source. "
            "Proceso en ingles. Trabajo remoto distribuido en todo el mundo."
        ),
    },
    {
        "slug": "08_BBVA_Mexico_FullStack_Junior",
        "title": "Desarrollador Full Stack Junior",
        "company": "BBVA Mexico",
        "url": "https://bbva.wd3.myworkdayjobs.com/es/BBVA/job/Desarrollador-a-Full-Stack-Junior_JR00103416",
        "platform": "workday",
        "description": (
            "Desarrollador Full Stack Junior en BBVA Mexico, banco lider en tecnologia "
            "financiera. Stack fullstack: backend con Java/Python y APIs REST, frontend con "
            "JavaScript/React, bases de datos SQL. Posicion junior ideal para primer empleo "
            "formal: trabajo en equipos agiles desarrollando productos digitales bancarios. "
            "Buscan ganas de aprender, bases de programacion, control de versiones con Git y "
            "trabajo en equipo. Modalidad hibrida en Mexico."
        ),
    },
    {
        "slug": "09_Oracle_GenO_Colombia_Pasantia",
        "title": "GenO - Programa de Pasantias (Generation Oracle)",
        "company": "Oracle Colombia",
        "url": "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch/job/332334/",
        "platform": "oracle",
        "description": (
            "Programa Generation Oracle (GenO) de pasantias y early career en Oracle "
            "Colombia. Programa de entrada para estudiantes y recien graduados en tecnologia: "
            "desarrollo de software, cloud, bases de datos y aplicaciones empresariales. "
            "Formacion y mentoria en tecnologias Oracle Cloud. Ideal para primer acercamiento "
            "profesional al mundo corporativo tech. Buscan estudiantes de ultimos semestres o "
            "egresados de Ingenieria de Software/Sistemas con bases de programacion."
        ),
    },
    {
        "slug": "10_Loft_Brasil_FullStack_Remote",
        "title": "Software Engineer - Full Stack (Remote)",
        "company": "Loft Brasil",
        "url": "https://loft.teamtailor.com/jobs/7014721-software-engineer-full-stack-remote-work",
        "platform": "teamtailor",
        "description": (
            "Software Engineer Full Stack, 100% remoto, en Loft, proptech brasilena de "
            "compra-venta de inmuebles. Stack fullstack moderno: backend (Python/Node), "
            "frontend (React/TypeScript), APIs REST, PostgreSQL, Docker y cloud. Trabajo "
            "remoto desde LATAM. Buscan ingenieros con base solida en desarrollo web "
            "fullstack, buenas practicas y autonomia. Ambiente colaborativo y producto de "
            "alto impacto. Comunicacion puede requerir ingles y/o portugues."
        ),
    },
    {
        "slug": "11_Addi_Colombia_CyberSec_Automation",
        "title": "CyberSecurity Automation Engineer (Remote)",
        "company": "Addi Colombia",
        "url": "https://co.addi.com/sobre-addi/trabaja-con-nosotros/de2e6ca3-a558-442c-ad60-5e7e87069407",
        "platform": "addi",
        "description": (
            "CyberSecurity Automation Engineer, 100% remoto, en Addi, fintech colombiana de "
            "creditos y pagos. Rol que combina seguridad y automatizacion: scripting en "
            "Python para automatizar tareas de seguridad, analisis de vulnerabilidades, "
            "integracion de herramientas de seguridad en pipelines. Stack: Python, Linux, "
            "herramientas de seguridad (escaneo, hardening), cloud. Ideal para perfiles con "
            "base en Python/Linux e interes o formacion en ciberseguridad."
        ),
    },
]

# Stack extra para reforzar el matching (el matcher mira title+description)
STACK_HINT = "Python Django FastAPI React Next.js TypeScript Node.js PostgreSQL Docker Linux Git REST APIs Flutter"

cv = profile.load()
if "error" in cv:
    print(f"[!] Error cargando CV: {cv['error']}")
    sys.exit(1)

print(f"CV cargado: {len(cv.get('techs', []))} tecnologias\n")

results = []
for job in jobs:
    print("=" * 64)
    print(f"{job['title']} en {job['company']}  [{job['platform']}]")

    match = matcher.score(
        {"title": job["title"] + " " + STACK_HINT, "description": job["description"]},
        cv,
    )
    print(f"  Compatibilidad: {match['score']}% ({match['fit']})")
    print(f"  Techs: {match['matched_techs'][:8]}")

    if match["fit"] == "baja":
        print("  [x] Descartada - baja compatibilidad\n")
        continue

    print("  Generando carta con DeepSeek...")
    try:
        carta = cover.generate(job, cv)
        out_path = os.path.join(OUT_DIR, job["slug"] + ".txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(carta)
        print(f"  Carta guardada: output/cartas/{job['slug']}.txt ({len(carta)} chars)\n")
        results.append({"job": job, "match": match, "carta": carta, "path": out_path})
    except Exception as e:
        print(f"  [!] Error generando carta: {e}\n")

print("=" * 64)
print(f"RESUMEN: {len(results)}/{len(jobs)} cartas generadas")
for r in results:
    j = r["job"]
    auto = "AUTO" if j["platform"] == "teamtailor" else "manual"
    print(f"  [{auto:6}] {j['company']:22} {j['title'][:40]:40} {r['match']['score']}%")
