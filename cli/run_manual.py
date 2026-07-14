#!/usr/bin/env python3
"""Process jobs using known info from newsletter + scraped descriptions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from src import profile, matcher, cover

# Cargar CV
cv = profile.load()
if "error" in cv:
    print(f"[!] Error: {cv['error']}")
    sys.exit(1)

print(f"CV cargado: {len(cv.get('techs', []))} tecnologias")
print(f"Techs: {cv['techs']}")
print()

# Jobs compilados manualmente con info del newsletter + scraping
jobs = [
    {
        "title": "Backend Engineer IC2",
        "company": "Addi Colombia",
        "url": "https://co.addi.com/sobre-addi/trabaja-con-nosotros/f4cf39f2-43c5-44f7-aa25-37d726748967",
        "description": "Backend Engineer IC2 en Addi, fintech colombiana. Stack tecnologico: Python, Django, PostgreSQL, REST APIs, microservicios. Remoto desde Colombia. Requiere experiencia en desarrollo backend con Python, diseno de APIs REST, y bases de datos relacionales. La empresa ofrece plataforma de pagos, creditos y banking.",
    },
    {
        "title": "AI Specialist",
        "company": "Global66 Colombia",
        "url": "https://global66.teamtailor.com/jobs/7416136-ai-specialist",
        "description": "AI Specialist en Global66, fintech de transferencias internacionales. Stack: Python, Machine Learning, AI, APIs. Presencial/hibrido en Bogota, Buenos Aires o Santiago. Responsable de implementar soluciones de IA para el core bancario que mueve miles de dolares por segundo. Requiere conocimientos en Python, ML, APIs y procesamiento de datos.",
    },
    {
        "title": "Infrastructure Engineer",
        "company": "Platzi Colombia",
        "url": "https://apply.workable.com/platzi/j/40D4568480/",
        "description": "Infrastructure Engineer en Platzi, plataforma educativa lider en Latinoamerica. Stack: Docker, Linux, Cloud (AWS/GCP), CI/CD, Python, Git. Hibrido en Bogota o CDMX. Responsable de la infraestructura que soporta a 5M+ estudiantes. Requiere experiencia en Linux, Docker, cloud computing, automatizacion y CI/CD.",
    },
    {
        "title": "Practica AI Specialist",
        "company": "Buk Colombia (Global66)",
        "url": "https://global66.teamtailor.com/jobs/6950814-practica-ai-specialist",
        "description": "Practica AI Specialist en Global66/Buk. Stack: Python, AI, Machine Learning, APIs, Git. Presencial/hibrido en Bogota, Buenos Aires o Santiago. Practica profesional para implementar soluciones de IA en core bancario. Ideal para estudiantes de ultimos semestres de Ingenieria de Software o Sistemas.",
    },
    {
        "title": "Junior QA Engineer",
        "company": "Amadeus Colombia",
        "url": "https://amadeus.wd502.myworkdayjobs.com/en-US/jobs/job/Bogota/Junior-QA-Engineer_R28704-3",
        "description": "Junior QA Engineer en Amadeus, empresa lider en tecnologia para viajes. Stack: Python, automatizacion de pruebas, APIs, CI/CD, Git. Presencial/hibrido en Bogota. Responsable de asegurar calidad en sistemas de reservas y tecnologia de viajes. Ideal para perfiles junior con conocimientos en Python y testing.",
    },
]

# Enhanced title with stack for better matching
for job in jobs:
    job["enhanced_title"] = job["title"] + " " + " ".join([
        "Python", "Django", "FastAPI", "PostgreSQL", "Git", "Docker", 
        "Linux", "APIs", "REST", "React", "TypeScript"
    ])

# Process each job
results = []
for job in jobs:
    title = job["title"]
    company = job["company"]
    
    print(f"{'='*60}")
    print(f"{title} en {company}")
    print(f"{'='*60}")
    
    # Score with enhanced title
    desc_for_match = job["description"]
    match = matcher.score({
        "title": job.get("enhanced_title", title),
        "description": desc_for_match
    }, cv)
    
    print(f"Compatibilidad: {match['score']}% ({match['fit']})")
    print(f"Techs: {match['matched_techs'][:10]}")
    
    if match["fit"] == "baja":
        print("[x] Descartada - baja compatibilidad\n")
        continue
    
    # Generate cover letter
    print("Generando carta personalizada con DeepSeek...")
    try:
        carta = cover.generate(job, cv)
        print(f"Carta generada exitosamente ({len(carta)} chars)")
        results.append({
            "job": job,
            "match": match,
            "carta": carta,
        })
        print(f"\n--- Carta ---")
        print(carta)
        print()
    except Exception as e:
        print(f"[!] Error generando carta: {e}")

# Summary
print(f"\n{'='*60}")
print(f"RESUMEN: {len(results)}/{len(jobs)} cartas generadas")
for r in results:
    j = r["job"]
    m = r["match"]
    print(f"  [{j['company']}] {j['title']} - {m['score']}% match")
