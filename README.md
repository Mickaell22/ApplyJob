# ApplyJob

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue?style=flat&logo=python&logoColor=white)](https://python.org)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-FF6F00?style=flat&logo=deepseek&logoColor=white)](https://deepseek.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat)](LICENSE)
[![GitHub repo](https://img.shields.io/github/stars/Mickaell22/ApplyJob?style=flat&logo=github)](https://github.com/Mickaell22/ApplyJob)

Automatizacion de postulaciones laborales. Recibe links de ofertas, las analiza contra tu perfil, genera cartas personalizadas con IA y las envia por correo.

---

## Pipeline

```
      URL        +-----------+    +----------+    +---------+    +---------+
ofertas --------->| Scraper  |--->| Matcher  |--->| Cover   |--->| Sender  |---> Gmail
                  +-----------+    +----------+    +---------+    +---------+
                        |               |               |              |
                   extrae titulo,   compara vs      genera carta    envia con
                   empresa, stack   perfil y CV     personalizada   CV adjunto
                                                        (DeepSeek)
```

## Arquitectura

```
ApplyJob/
├── main.py              # orquestador del pipeline
├── profile/
│   └── cv.md            # perfil del candidato (stack, experiencia, skills)
├── src/
│   ├── scraper.py       # extrae informacion de ofertas desde URLs
│   ├── profile.py       # carga y parsea el CV/perfil
│   ├── matcher.py       # calcula compatibilidad oferta vs perfil
│   ├── cover.py         # genera carta de presentacion via DeepSeek Flash
│   └── sender.py        # envia correo via Gmail SMTP
└── .env                 # variables de entorno (no versionado)
```

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| Lenguaje | [Python](https://python.org) 3.12+ |
| IA generativa | [DeepSeek Flash](https://platform.deepseek.com) via Anthropic SDK |
| Web scraping | [httpx](https://www.python-httpx.org) + [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) |
| Correo | Gmail SMTP + Google App Password |
| Entorno | Linux Mint, ZeroTier, systemd |

## Instalacion

```bash
git clone https://github.com/Mickaell22/ApplyJob.git
cd ApplyJob

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuracion

Crear archivo `.env` en la raiz del proyecto:

```
DEEPSEEK_API_KEY=sk-...
GMAIL_USER=tu-correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
CV_PATH=./profile/cv.md
```

### Como obtener las credenciales

- **DeepSeek API key**: [platform.deepseek.com](https://platform.deepseek.com) -> API Keys
- **Gmail App Password**: https://myaccount.google.com/apppasswords (requiere 2FA activado)

## Uso

### CLI directo

```bash
# Una oferta
python main.py https://juniorjobs.short.gy/LbO1f3

# Varias ofertas
python main.py https://juniorjobs.short.gy/LbO1f3 https://juniorjobs.short.gy/gjno2F

# Desde stdin
echo "url1 url2" | python main.py
```

### Integracion desde codigo

```python
from src import profile, scraper, matcher, cover, sender

cv = profile.load()
job = scraper.fetch_job("https://juniorjobs.short.gy/LbO1f3")
match = matcher.score(job, cv)

if match["fit"] in ("alta", "media"):
    carta = cover.generate(job, cv)
    sender.send(
        to_email="hr@empresa.com",
        subject=f"Candidatura: {job['title']}",
        body=carta,
        attachment="./profile/cv.pdf",
    )
```

## Perfil del candidato

Editar `profile/cv.md` con tu informacion:

- Stack tecnologico
- Experiencia laboral
- Educacion y certificaciones
- Preferencias (remoto, presencial, ubicacion)

El matcher usa este archivo para calcular la compatibilidad con cada oferta.

## Compatibilidad

El sistema evalua cada oferta contra tu perfil y asigna un score:

- **Alta** (>40%): procede a generar carta y enviar
- **Media** (20-40%): procede con precaucion
- **Baja** (<20%): descartada automaticamente

## Licencia

MIT
