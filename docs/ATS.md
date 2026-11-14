# Relleno asistido de formularios ATS (opt-in, experimental)

[Volver al README](../README.md)


> El flujo por defecto **no** postula por vos: `run_discover.py` lista candidatas, vos
> revisas los links y postulas a mano. `src/apply_ats.py` es un modulo aparte que rellena
> los campos repetitivos de un formulario (nombre, contacto, CV) para no retipearlos en
> cada ATS. Se usa en `dry_run=True` mientras se prueba un handler nuevo.

```python
from src.apply_ats import run

jobs_with_letters = [
    {"job": {"title": "...", "company": "...", "url": "..."}, "carta": "cover letter text..."}
]

# Dry run (llena formulario pero NO envia)
result = run(jobs_with_letters, dry_run=True)

# Envio real
result = run(jobs_with_letters, dry_run=False)
```

## Plataformas ATS soportadas

| Plataforma | Estado | Empresas |
|---|---|---|
| Workable | Funcional | Platzi, Canonical, Loft |
| Greenhouse | Implementado | Canonical |
| Teamtailor | No funcional (cookie wall) | Global66, Loft |
| Ashby | Pendiente | Addi |
| Workday | No viable (login/anti-bot) | Amadeus, Oracle, BBVA |

> Nota: Workday y Oracle Cloud exigen crear cuenta con login + verificacion email, por lo que
> no son automatizables de forma confiable; se postulan manualmente.
