"""Genera cartas de presentacion personalizadas usando DeepSeek Flash."""

import os
import re
from anthropic import Anthropic


client = Anthropic(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com/anthropic",
)

_PROHIBITED_TECH = {
    "kubernetes", "golang", ".net", "angular", "oracle", "hibernate",
    "jenkins", "sonarqube", "maven", "redis", "storybook", "grafana",
    "kafka", "terraform", "spring boot", "graphql",
}

_HONESTY_RULES_ES = (
    "- El candidato es JUNIOR / en formacion. Menos de 2 anos de experiencia profesional.\n"
    "- NO inventar anos de experiencia. Preferir 'mas de 1 ano' antes que 'mas de 2 anos'.\n"
    "- NO mencionar tecnologias que NO esten en el perfil del candidato (seccion Stack/Skills).\n"
    "- Tecnologias PROHIBIDAS (no mencionar nunca): Kubernetes, Golang, .NET, Angular, Oracle,\n"
    "  Hibernate, Jenkins, Sonarqube, Maven, Redis, Storybook, Grafana, Kafka, Terraform,\n"
    "  Spring Boot avanzado, GraphQL avanzado, AWS serverless avanzado.\n"
    "- NO usar palabras como: domino, experto, avanzado, lideré (excepto si el CV lo dice),\n"
    "  sobresaliente, solide, consolidada. Usar: 'trabaje con', 'contribui a',\n"
    "  'tengo experiencia basica en', 'estoy familiarizado con', 'he utilizado'.\n"
    "- Tono humilde, de aprendizaje continuo. Destacar proyectos personales y practicas reales.\n"
    "- Si la oferta pide anos de experiencia que el candidato no tiene, NO mentir ni inflar.\n"
)

_HONESTY_RULES_EN = (
    "- The candidate is JUNIOR / in training. Less than 2 years of professional experience.\n"
    "- Do NOT invent years of experience. Prefer 'over 1 year' instead of 'over 2 years'.\n"
    "- Do NOT mention technologies NOT listed in the candidate's profile (Stack/Skills section).\n"
    "- PROHIBITED technologies (never mention): Kubernetes, Golang, .NET, Angular, Oracle,\n"
    "  Hibernate, Jenkins, Sonarqube, Maven, Redis, Storybook, Grafana, Kafka, Terraform,\n"
    "  advanced Spring Boot, advanced GraphQL, advanced AWS serverless.\n"
    "- Do NOT use words like: mastery, expert, advanced, led (unless the CV explicitly says so),\n"
    "  outstanding, solid X years. Use instead: 'worked with', 'contributed to',\n"
    "  'have basic experience with', 'am familiar with', 'have used'.\n"
    "- Humble tone focused on continuous learning. Highlight personal projects and real internships.\n"
    "- If the offer requires years of experience the candidate does not have, do NOT lie or inflate.\n"
)


def _unknown_tech_note(job_desc: str, lang: str) -> str:
    found = [t for t in _PROHIBITED_TECH if t in job_desc.lower()]
    if not found:
        return ""
    techs = ", ".join(found)
    if lang == "en":
        return (
            f"- The job mentions: {techs}. The candidate does NOT have experience with these.\n"
            "  If relevant, say the candidate is willing to learn them, but do NOT claim proficiency.\n"
        )
    return (
        f"- La oferta menciona: {techs}. El candidato NO tiene experiencia en estas tecnologias.\n"
        "  Si es relevante, mencionar disposicion para aprenderlas, pero NO afirmar que las domina.\n"
    )


def generate(job: dict, profile: dict, lang: str = "es") -> str:
    """Genera carta de presentacion para una oferta especifica.

    lang: "es" para espanol (default), "en" para ingles (ej: Canonical, ofertas en ingles).
    """

    raw = profile.get("raw", "")
    nombre = profile.get("name", _extract(raw, r"^#\s+(.+)", os.getenv("CANDIDATE_NAME", "")))
    email = profile.get("email", _extract(raw, r"[\w.+-]+@[\w-]+\.[\w.]+", os.getenv("GMAIL_USER", "")))
    telefono = _extract(raw, r"\+?\d[\d\s()-]{7,}", os.getenv("CANDIDATE_PHONE", ""))
    linkedin = _extract(raw, r"https?://(?:www\.)?linkedin\.com[^\s]+", os.getenv("CANDIDATE_LINKEDIN", ""))
    github = _extract(raw, r"https?://(?:www\.)?github\.com[^\s]+", os.getenv("CANDIDATE_GITHUB", ""))
    portfolio = os.getenv("CANDIDATE_WEBSITE", "")
    _city = os.getenv("CANDIDATE_CITY", "")
    _country = os.getenv("CANDIDATE_COUNTRY", "")
    ubicacion = os.getenv("CANDIDATE_LOCATION") or ", ".join(filter(None, [_city, _country]))

    unknown_note = _unknown_tech_note(job.get("description", ""), lang)

    if lang == "en":
        intro = (
            "You are an assistant that helps apply to jobs. "
            "Write a professional cover letter in English, tailored to the offer.\n\n"
            "RULES:\n"
            "- No emojis\n"
            "- Maximum 250 words\n"
            "- Use the candidate's real data, do NOT use placeholders or brackets\n"
            "- Real contact details at the end of the letter\n"
            + _HONESTY_RULES_EN
            + unknown_note
            + "\n"
        )
        closing = (
            "The letter must include: greeting, introduction, why the candidate fits the role, "
            "relevant experience, and a cordial closing with the candidate's real contact details "
            "including portfolio URL."
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
            "- Datos de contacto reales al final de la carta\n"
            + _HONESTY_RULES_ES
            + unknown_note
            + "\n"
        )
        closing = (
            "La carta debe incluir: saludo, presentacion, porque encaja con el puesto, "
            "experiencia relevante, cierre cordial con datos de contacto reales del candidato "
            "incluyendo URL del portafolio."
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
                f"**Portfolio:** {portfolio}\n"
                f"**Ubicacion:** {ubicacion}\n"
                f"**Perfil completo:** {raw}\n\n"
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
