#!/usr/bin/env python3
"""Archiva las cartas del día para empezar limpio mañana.

Mueve output/cartas/disc_*.txt a output/cartas/archive/YYYY-MM-DD/

Uso:
  python clean_letters.py           # archiva con fecha de hoy
  python clean_letters.py --delete  # borra en lugar de archivar
"""

import os
import sys
import shutil
from datetime import date
from pathlib import Path

CARTAS_DIR = Path(__file__).resolve().parent.parent / "output" / "cartas"
DELETE = "--delete" in sys.argv

letters = sorted(CARTAS_DIR.glob("disc_*.txt"))

if not letters:
    print("No hay cartas que limpiar.")
    sys.exit(0)

if DELETE:
    for f in letters:
        f.unlink()
    print(f"Borradas {len(letters)} cartas.")
else:
    archive_dir = CARTAS_DIR / "archive" / str(date.today())
    archive_dir.mkdir(parents=True, exist_ok=True)
    for f in letters:
        shutil.move(str(f), archive_dir / f.name)
    print(f"Archivadas {len(letters)} cartas → {archive_dir}")
