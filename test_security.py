#!/usr/bin/env python3
"""
Prueba de ApplyJob con tematica de ciberseguridad.
Envia un test al propio correo del candidato.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from src import profile, cover, sender

# Simular una oferta de ciberseguridad
job = {
    "title": "Analista de Ciberseguridad SOC",
    "company": "CipherGuard LATAM",
    "url": "https://ejemplo.com/oferta-ciberseguridad",
    "description": """
Buscamos un Analista de Ciberseguridad para unirse a nuestro equipo SOC en modalidad remota.

Requisitos:
- Experiencia en monitoreo de eventos de seguridad (SIEM: Splunk, QRadar, Wazuh)
- Conocimiento en análisis de malware y forense digital
- Familiaridad con frameworks: NIST, MITRE ATT&CK, ISO 27001
- Manejo de herramientas EDR (CrowdStrike, SentinelOne, Defender)
- Linux, Python, scripting
- Certificaciones deseables: Security+, CEH, OSCP

Ofrecemos:
- Salario competitivo ($2,500 - $4,000 USD/mes)
- Trabajo 100% remoto
- Capacitación continua y certificaciones pagadas
- Seguro médico y bonos por desempeño
    """,
}

cv = profile.load()
if "error" in cv:
    print(f"[!] Error cargando perfil: {cv['error']}")
    sys.exit(1)

print("[+] Cargando perfil... OK")
print(f"[+] Generando carta de ciberseguridad...")

carta = cover.generate(job, cv)

print(f"\n--- CARTA GENERADA ---\n{carta}\n---\n")

email = cv.get("email") or os.getenv("GMAIL_USER")
print(f"[+] Enviando a {email}...")

result = sender.send(
    to_email=email,
    subject=f"[TEST] Candidatura: {job['title']} en {job['company']}",
    body=carta,
    attachment=os.getenv("CV_PATH", "profile/cv.md"),
)

if result.get("ok"):
    print(f"\n[v] Prueba exitosa. Correo enviado a {result['to']}")
    print(f"    Asunto: {result['subject']}")
else:
    print(f"\n[!] Error: {result.get('error')}")
