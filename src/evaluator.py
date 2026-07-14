"""Evaluacion on-demand de UNA oferta vs el perfil: reglas duras + DeepSeek.

Se usa SOLO desde cli/gen_cover.py para las 1-3 ofertas finalistas — nunca sobre el
batch completo de descubrimiento (romperia la optimizacion de costo del 25-jun).

Flujo:
  1. hard_skip_reasons(job)      — reglas deterministas, 0 API. Si hay razones,
                                   la decision es Skip sin llamar al LLM.
  2. evaluate(job, profile)      — DeepSeek razona CV vs oferta en dimensiones
                                   ponderadas y devuelve JSON (prompt ordenado
                                   para cache: constante primero, oferta al final).
  3. evaluate_with_overrides()   — combina ambas; entrada unica para gen_cover.
"""

import json
import os
import re

from src import boards

_DECISIONS = ("Apply", "Consider", "Research", "Skip")

# ponytail: heuristica naive para detectar "prohibido usar IA" en la descripcion
# (caso Canonical). Techo: frases inusuales se escapan; upgrade seria pedirselo
# al LLM en evaluate(), pero la regla dura debe ser 0 API y determinista.
_AI_BAN = re.compile(
    r"(?:ai|llm)[-\s]generated|generated\s+(?:by|with|using)\s+ai|"
    r"use\s+of\s+ai\b.{0,120}?(?:disqualif|reject|not\s+accept)|"
    r"do\s+not\s+use\s+ai|without\s+(?:the\s+use\s+of\s+)?ai\s+(?:tools|assistance)|"
    r"prohibid\w*\b.{0,40}\bIA\b|sin\s+(?:usar|uso\s+de)\s+IA",
    re.I | re.S,
)


def hard_skip_reasons(job: dict) -> list[str]:
    """Reglas force-SKIP deterministas (0 API). Devuelve lista de razones.

    Formaliza los filtros dispersos de boards.py para la fase on-demand:
    - titulo senior/lead/architect/ssr
    - descripcion pide 3+ años de experiencia
    - la empresa prohibe contenido generado por IA
    - pais requerido incompatible con CANDIDATE_REGION (solo canal remoto;
      el canal local acepta el pais del candidato)
    """
    reasons: list[str] = []
    title = job.get("title", "") or ""
    desc = re.sub(r"<[^>]+>", " ", job.get("description", "") or "")

    if boards._SENIOR_EXCLUDE.search(title):
        reasons.append("titulo senior/lead/architect/ssr")
    if boards._EXP_EXCLUDE.search(desc):
        reasons.append("pide 3+ años de experiencia")
    if _AI_BAN.search(desc):
        reasons.append("la empresa prohibe contenido generado por IA")

    loc = job.get("location_required", "") or ""
    if (
        job.get("canal") != "local"
        and loc.strip()
        and not boards._LOCATION_OK.search(loc)
        and boards._LOCATION_EXCLUDE.search(loc)
    ):
        reasons.append(f"pais requerido incompatible: {loc}")

    return reasons


def evaluate(job: dict, profile: dict) -> dict:
    """Evalua CV vs oferta con DeepSeek. Devuelve dict con scores y decision.

    Prompt ordenado para cache de prefijo (igual que cover.py): lo CONSTANTE
    (instrucciones + perfil) primero, la OFERTA variable al final. NO meter
    nada dependiente del job en el bloque constante.
    """
    from anthropic import Anthropic  # import lazy: solo se paga al evaluar

    client = Anthropic(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com/anthropic",
    )

    constant_prefix = (
        "Evalua la compatibilidad entre un candidato y una oferta laboral.\n"
        "Responde SOLO un objeto JSON valido, sin markdown ni texto extra, con claves:\n"
        '{"match_cv": 1-5, "nivel_fit": 1-5, "remoto_real": 1-5, "comp": 1-5, "global": 0-5,\n'
        ' "red_flags": ["..."], "decision": "Apply|Consider|Research|Skip", "razon": "una linea"}\n\n'
        "Criterios:\n"
        "- El candidato es JUNIOR (<2 años de experiencia profesional). Se evalua honestidad,\n"
        "  no optimismo: si la oferta pide mas nivel del que hay, decir Skip.\n"
        "- match_cv: solapamiento REAL de stack y experiencia con el perfil.\n"
        "- nivel_fit: 5 = junior-friendly explicito; penaliza '3+ años', 'senior', 'lead'.\n"
        "- remoto_real: 5 = worldwide async; 1 = country-locked u onsite. EXCEPCION: si la\n"
        "  oferta viene marcada canal=local, onsite/hibrido en el pais del candidato es valido (4-5).\n"
        "- comp: compensacion vs mercado junior remoto (3 si no se menciona).\n"
        "- global: contratabilidad desde el pais del candidato (contratacion internacional,\n"
        "  huso horario, entidad legal). 0 = imposible.\n"
        "- red_flags: ej. 'prohibe IA', 'exige reubicacion', 'pais incompatible', 'stack ajeno'.\n"
        "- decision: Apply = encaja claro; Consider = dudas menores; Research = falta info\n"
        "  clave; Skip = no aplica.\n\n"
        "--- PERFIL DEL CANDIDATO ---\n"
        f"{profile.get('raw', '')}\n\n"
    )
    job_suffix = (
        "--- OFERTA A EVALUAR ---\n"
        f"Titulo: {job.get('title', '')}\n"
        f"Empresa: {job.get('company', '')}\n"
        f"Ubicacion requerida: {job.get('location_required', '') or 'no especificada'}\n"
        f"Canal: {job.get('canal', 'remoto')}\n"
        f"Descripcion: {job.get('description', '')[:2000]}\n"
    )

    resp = client.messages.create(
        model="deepseek-chat",
        max_tokens=400,
        messages=[{"role": "user", "content": constant_prefix + job_suffix}],
    )
    text = resp.content[0].text
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"decision": "Research", "razon": "el LLM no devolvio JSON", "red_flags": []}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"decision": "Research", "razon": "JSON invalido del LLM", "red_flags": []}
    if data.get("decision") not in _DECISIONS:
        data["decision"] = "Research"
    data.setdefault("red_flags", [])
    return data


def evaluate_with_overrides(job: dict, profile: dict) -> dict:
    """Entrada unica: reglas duras primero (0 API); si pasan, evalua con LLM.

    Umbral guia (career-ops adaptado a junior): promedio < 3.0 -> warning
    'threshold_warning' en el dict (no bloquea, la decision manda).
    """
    reasons = hard_skip_reasons(job)
    if reasons:
        return {
            "decision": "Skip",
            "red_flags": reasons,
            "razon": "regla dura: " + "; ".join(reasons),
            "forced": True,
        }

    data = evaluate(job, profile)

    dims = [data.get(k) for k in ("match_cv", "nivel_fit", "remoto_real", "comp", "global")]
    nums = [d for d in dims if isinstance(d, (int, float))]
    if nums:
        avg = round(sum(nums) / len(nums), 1)
        data["promedio"] = avg
        if avg < 3.0:
            data["threshold_warning"] = f"promedio {avg} < 3.0 (umbral junior)"
    return data


# Self-check de las reglas duras (0 API): correr `python3 -m src.evaluator`
if __name__ == "__main__":
    assert hard_skip_reasons({"title": "Senior Python Developer", "description": ""}), \
        "titulo senior debe forzar skip"
    assert hard_skip_reasons({"title": "Dev", "description": "minimo 4 años de experiencia"}), \
        "3+ años debe forzar skip"
    assert hard_skip_reasons(
        {"title": "Dev", "description": "AI-generated applications will be rejected"}
    ), "prohibicion de IA debe forzar skip"
    assert hard_skip_reasons(
        {"title": "Dev", "description": "", "location_required": "Germany"}
    ), "pais incompatible (canal remoto) debe forzar skip"
    assert not hard_skip_reasons(
        {"title": "Junior Dev", "description": "", "location_required": "Quito", "canal": "local"}
    ), "canal local no aplica geo-filtro"
    assert not hard_skip_reasons(
        {"title": "Junior Python Developer", "description": "entry level, Worldwide",
         "location_required": "Worldwide"}
    ), "junior worldwide debe pasar"
    print("evaluator.py self-check OK")
