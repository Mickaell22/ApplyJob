"""Check de TECH_FILTER: deja pasar pasantias tecnicas, bloquea las que no lo son.

Correr: .venv/bin/python3 tests/test_tech_filter.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.boards._common import TECH_FILTER, _SENIOR_EXCLUDE  # noqa: E402

# Pasantias/practicas reales que el filtro dejaba fuera antes (caso Grupo Lucky:
# "Pasante de Desarrollo (web y movil)" hubo que encontrarlo a mano).
PASAN = [
    "Pasante de Desarrollo (web y móvil)",
    "Pasante de Desarrollo de Software",
    "Practicante de Programación",
    "Prácticas Desarrollo Web",
    "Becario Desarrollo Web",
    "Pasantía en Sistemas Informáticos",
    "Software Engineering Intern",
    "Full Stack Developer Intern",
    "Internship - Backend",
    "Desarrollador Junior",
    "Analista de Sistemas Junior",
]

# Ruido no tecnico: la palabra "pasante" sola no debe alcanzar para entrar.
BLOQUEAN = [
    "Pasante de Marketing",
    "Pasante de Recursos Humanos",
    "Practicante Contable",
    "Pasantía en Ventas",
    "Asistente Administrativo",
]

# Los titulos senior siguen cayendo por _SENIOR_EXCLUDE aunque pasen TECH_FILTER.
SENIOR = [
    "Desarrollador Web Senior",
    "Líder de Desarrollo de Software",
    "Arquitecto de Sistemas",
]


def main() -> int:
    fallos = []

    for t in PASAN:
        if not TECH_FILTER.search(t):
            fallos.append(f"deberia PASAR y no pasa: {t!r}")

    for t in BLOQUEAN:
        m = TECH_FILTER.search(t)
        if m:
            fallos.append(f"deberia BLOQUEARSE y pasa por {m.group(0)!r}: {t!r}")

    for t in SENIOR:
        if not _SENIOR_EXCLUDE.search(t):
            fallos.append(f"deberia caer por senior y no cae: {t!r}")

    if fallos:
        print("FALLOS:")
        for f in fallos:
            print("  -", f)
        return 1

    print(f"OK — {len(PASAN)} pasan, {len(BLOQUEAN)} bloqueadas, {len(SENIOR)} senior descartadas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
