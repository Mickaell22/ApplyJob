# Instalacion y configuracion

[Volver al README](../README.md)

## Instalar

```bash
git clone https://github.com/Mickaell22/ApplyJob.git
cd ApplyJob

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Configurar

**1. Crea tu `.env`** copiando el ejemplo:

```bash
cp .env.example .env
# Edita .env con tu editor y llena todos los valores
```

**2. Crea tu perfil** a partir del template:

```bash
cp profile/cv_template.md profile/cv.md
# Edita profile/cv.md con tu experiencia, stack y datos de contacto
```

`profile/cv.md` es la única fuente de perfil: las cartas en inglés se generan desde ese
mismo archivo con `lang="en"`.

**3. Pon tus CVs en PDF:**

```
profile/cv_es.pdf   ← CV en español (o tu idioma principal)
profile/cv_en.pdf   ← CV en inglés (opcional, para ofertas EN)
```

Las rutas se configuran en `.env` con `CV_PATH` y `CV_PATH_EN`.

### Variables del `.env`

```env
# IA
DEEPSEEK_API_KEY=sk-...

# Correo
GMAIL_USER=tu-correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# CVs en PDF (español e inglés)
CV_PATH=./profile/cv_es.pdf
CV_PATH_EN=./profile/cv_en.pdf

# Datos del candidato — usados en cartas y formularios ATS
CANDIDATE_NAME=Tu Nombre
CANDIDATE_PHONE=+1 234 567 8900
CANDIDATE_LOCATION=Ciudad, País
CANDIDATE_CITY=Ciudad
CANDIDATE_COUNTRY=País
CANDIDATE_LINKEDIN=https://linkedin.com/in/tu-perfil
CANDIDATE_GITHUB=https://github.com/tu-usuario
CANDIDATE_WEBSITE=https://tu-portafolio.com

# Región geográfica — filtra ofertas inaccesibles para tu ubicación
# Opciones: LATAM (default), EUROPE, ASIA, USA, GLOBAL
CANDIDATE_REGION=LATAM
```

### Como obtener las credenciales

- **DeepSeek API key**: [platform.deepseek.com](https://platform.deepseek.com) -> API Keys
- **Gmail App Password**: https://myaccount.google.com/apppasswords (requiere 2FA activado)

## Perfil del candidato

Editar `profile/cv.md` con tu informacion:

- Stack tecnologico
- Experiencia laboral
- Educacion y certificaciones
- Preferencias (remoto, presencial, ubicacion)

El matcher usa este archivo para calcular la compatibilidad con cada oferta.
