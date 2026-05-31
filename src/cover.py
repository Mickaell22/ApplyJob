"""Genera cartas de presentacion personalizadas usando DeepSeek Flash."""

import os
import re
from anthropic import Anthropic


client = Anthropic(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com/anthropic",
)


def generate(job: dict, profile: dict, lang: str = "es") -> str:
    """Genera carta de presentacion para una oferta especifica.

    lang: "es" para espanol (default), "en" para ingles (ej: Canonical, ofertas en ingles).
    """

    raw = profile.get("raw", "")
    nombre = profile.get("name", _extract(raw, r"^#\s+(.+)", "Mickaell Moran"))
    email = profile.get("email", _extract(raw, r"[\w.+-]+@[\w-]+\.[\w.]+", "mickaelmoranvera03@gmail.com"))
    telefono = _extract(raw, r"\+?\d[\d\s()-]{7,}", "+593 98 377 7036")
    linkedin = _extract(raw, r"https?://(?:www\.)?linkedin\.com[^\s]+", "")
    github = _extract(raw, r"https?://(?:www\.)?github\.com[^\s]+", "")
    ubicacion = "Guayaquil, Ecuador"

    if lang == "en":
        intro = (
            "You are an assistant that helps apply to jobs. "
            "Write a professional cover letter in English, tailored to the offer.\n\n"
            "RULES:\n"
            "- No emojis\n"
            "- Maximum 250 words\n"
            "- Use the candidate's real data, do NOT use placeholders or brackets\n"
            "- Real contact details at the end of the letter\n\n"
        )
        closing = (
            "The letter must include: greeting, introduction, why the candidate fits the role, "
            "relevant experience, and a cordial closing with the candidate's real contact details."
        )
    else:
        intro = (
            "Eres un asistente que ayuda a postularse a trabajos. "
            "Genera una carta de presentacion profesional en espanol, "
            "personalizada para la oferta.\n\n"
            "REGLAS:\n"
            "- Sin emojis\n"
            "- Maximo 250 palabras\n"
            "- Usa los datos reales del candidato, NO uses placeholders ni corchetes\n"
            "- Datos de contacto reales al final de la carta\n\n"
        )
        closing = (
            "La carta debe incluir: saludo, presentacion, porque encaja con el puesto, "
            "experiencia relevante, cierre cordial con datos de contacto reales del candidato."
        )

    resp = client.messages.create(
        model="deepseek-chat",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": (
                intro
                + f"**Oferta:** {job.get('title', '')} en {job.get('company', '')}\n"
                f"**Descripcion:** {job.get('description', '')[:2000]}\n"
                f"**Nombre candidato:** {nombre}\n"
                f"**Email:** {email}\n"
                f"**Telefono:** {telefono}\n"
                f"**LinkedIn:** {linkedin}\n"
                f"**GitHub:** {github}\n"
                f"**Ubicacion:** {ubicacion}\n"
                f"**Perfil completo:** {raw[:1500]}\n\n"
                + closing
            ),
        }],
    )
    return resp.content[0].text


def _extract(text: str, pattern: str, default: str = "") -> str:
    m = re.search(pattern, text, re.I | re.M)
    if not m:
        return default
    try:
        return m.group(1).strip()
    except IndexError:
        return m.group(0).strip()
