#!/usr/bin/env python3
"""Test the auto-apply module with Platzi (Workable)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from src.apply_ats import run

# Read the saved cover letter for Platzi
with open("output/cartas/03_Platzi_Infrastructure_Engineer.txt") as f:
    letter = f.read()

job = {
    "title": "Infrastructure Engineer",
    "company": "Platzi Colombia",
    "url": "https://apply.workable.com/platzi/j/40D4568480/",
}

result = run([{"job": job, "carta": letter}], dry_run=True)
print(f"\nFinal result: {result}")
