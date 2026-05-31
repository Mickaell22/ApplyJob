#!/usr/bin/env python3
"""Batch process job URLs through ApplyJob pipeline."""
import sys, os, httpx
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from src import profile, matcher, cover, sender

# Job list: (short_url, title, company)
job_list = [
    ('https://juniorjobs.short.gy/D3yP08', 'Backend Engineer IC2', 'Addi Colombia'),
    ('https://juniorjobs.short.gy/dGhrhb', 'AI Specialist', 'Global66 Colombia'),
    ('https://juniorjobs.short.gy/g1YBZq', 'Practica AI Specialist', 'Buk Colombia'),
    ('https://juniorjobs.short.gy/zcs1ex', 'Infrastructure Engineer', 'Platzi Colombia'),
    ('https://juniorjobs.short.gy/Znyvxs', 'Junior QA Engineer', 'Amadeus Colombia'),
]

# Resolve short URLs
resolved = []
for short, title, company in job_list:
    try:
        r = httpx.head(short, follow_redirects=True, timeout=10)
        resolved.append((str(r.url), title, company))
        print(f'{company} - {title}')
        print(f'  URL: {r.url}')
    except Exception as e:
        print(f'  Error resolving {short}: {e}')

print()

# Scrape with Playwright
jobs = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    
    for url, title, company in resolved:
        print(f'Scraping {company} - {title}...')
        try:
            page = browser.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            page.close()
            
            soup = BeautifulSoup(html, 'html.parser')
            body = soup.find('body')
            text = body.get_text(separator=' ', strip=True) if body else ''
            
            # Extract description
            desc_selectors = [
                'div[class*=description]', 'div[class*=content]', 'div[class*=job]',
                'section[class*=description]', 'article', 'main',
                'div[data-ui=job-description]'
            ]
            desc_text = ''
            for sel in desc_selectors:
                els = soup.select(sel)
                for el in els:
                    t = el.get_text(separator=' ', strip=True)
                    if len(t) > 200:
                        desc_text = t
                        break
                if desc_text:
                    break
            if not desc_text:
                desc_text = text[:3000]
            
            h1 = soup.find('h1')
            real_title = h1.get_text(strip=True) if h1 else title
            
            jobs.append({
                'url': url,
                'title': real_title,
                'company': company,
                'description': desc_text[:5000],
            })
            print(f'  OK - {len(desc_text)} chars description')
        except Exception as e:
            print(f'  Error: {e}')
    
    browser.close()

# Load CV
cv = profile.load()
if "error" in cv:
    print(f"[!] Error cargando CV: {cv['error']}")
    sys.exit(1)

techs_count = len(cv.get("techs", []))
print(f'\nCV cargado: {techs_count} tecnologias')

# Process each job
results = []
for job in jobs:
    print(f'\n=== {job["title"]} en {job["company"]} ===')
    
    match = matcher.score(job, cv)
    print(f'Compatibilidad: {match["score"]}% ({match["fit"]})')
    print(f'Techs coincidentes: {match["matched_techs"][:8]}')
    
    if match["fit"] in ("baja",):
        print('[x] Descartada - baja compatibilidad')
        continue
    
    print('Generando carta...')
    try:
        carta = cover.generate(job, cv)
        print(f'Carta generada ({len(carta)} chars)')
        results.append({
            'job': job,
            'match': match,
            'carta': carta,
        })
        print(f'--- Preview carta ---')
        print(carta[:400])
        print('...')
    except Exception as e:
        print(f'[!] Error: {e}')

# Summary
print(f'\n{"="*50}')
print(f'RESUMEN: {len(results)}/{len(jobs)} cartas generadas')
for r in results:
    j = r['job']
    print(f'  [{j["company"]}] {j["title"]} - {r["match"]["score"]}% match')
