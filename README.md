# ApplyJob

Automatización de postulaciones laborales. Recibe una lista de ofertas, las analiza contra tu perfil, genera cartas personalizadas y envía los correos automáticamente.

## Flujo

1. Envías los links del boletín semanal por Telegram
2. ApplyJob analiza cada oferta contra tu perfil (stack, experiencia, ubicación)
3. Filtra solo las que encajan
4. Genera carta de presentación personalizada por oferta
5. Envía el correo con tu CV adjunto desde Gmail

## Stack

- Python 3.12+
- DeepSeek Flash (generación de cartas vía Anthropic SDK)
- Gmail SMTP + App Password
- BeautifulSoup / httpx para scraping de ofertas

## Uso

```bash
python main.py <<< "https://juniorjobs.short.gy/LbO1f3 https://juniorjobs.short.gy/vGvJmF"
```

O desde Telegram directamente (cuando esté integrado).

## Configuración

Crear `.env` en la raíz:

```
DEEPSEEK_API_KEY=sk-...
GMAIL_USER=mickaelmoranvera03@gmail.com
GMAIL_APP_PASSWORD=tu-app-password
CV_PATH=./profile/cv.pdf
```

## Perfil

Editar `profile/cv.md` con tu stack, experiencia, skills y preferencias. Ahí se basa el análisis de compatibilidad.
