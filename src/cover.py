"""Genera cartas de presentacion personalizadas usando DeepSeek Flash."""

import os
from anthropic import Anthropic


client = Anthropic(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/anthropic",
)


def generate(job: dict, profile: dict) -> str:
    """Genera carta de presentacion para una oferta especifica."""
    resp = client.messages.create(
        model="deepseek-chat",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": (
                "Eres un asistente que ayuda a postularse a trabajos. "
                "Genera una carta de presentacion profesional en espanol, "
                "personalizada para la oferta. Sin emojis. Maximo 250 palabras.\n\n"
                f"**Oferta:** {job.get('title', '')} en {job.get('company', '')}\n"
                f"**Descripcion:** {job.get('description', '')[:2000]}\n"
                f"**Perfil del candidato:** {profile.get('full_text', '')[:1500]}\n\n"
                "La carta debe incluir: saludo, presentacion, porque encaja con el puesto, "
                "experiencia relevante, cierre cordial con datos de contacto."
            ),
        }],
    )
    return resp.content[0].text
