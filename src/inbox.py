"""Lee correos de Gmail via IMAP para dar seguimiento a postulaciones.

Busca correos de respuestas a postulaciones (entrevistas, rechazos, seguimientos).
Se puede llamar manualmente o via cron.
"""

import os
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone
import re

# Palabras clave para detectar correos relacionados a postulaciones
_JOB_KEYWORDS = [
    "candidatura", "aplicacion", "postulacion", "aplicación", "postulación",
    "job", "application", "apply", "candidate", "hiring", "recruitment",
    "interview", "entrevista", "offer", "oferta", "position", "puesto",
    "thank you for applying", "gracias por aplicar", "we received",
    "next steps", "siguientes pasos", "assessment", "challenge",
    "technical test", "prueba tecnica", "coding challenge",
    "invitation", "invitacion", "schedule", "agendar",
]

# Palabras clave de remitentes comunes de postulaciones
_SENDER_KEYWORDS = [
    "greenhouse", "lever", "bamboohr", "workable", "smartrecruiters",
    "linkedin", "indeed", "infojobs", "teamtailor", "jobvite",
    "recruitee", "breezy", "comeet", "ashby", "pinpointe",
    "jobadder", "icims", "taleo", "successfactors", "workday",
]


def check_inbox(max_emails: int = 30) -> list[dict]:
    """Revisa la bandeja de entrada y devuelve correos de postulaciones recientes."""
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not user or not password:
        return [{"error": "Faltan credenciales GMAIL"}]

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, password)
        mail.select("INBOX")

        # Buscar correos de los ultimos 7 dias
        status, messages = mail.search(None, "SINCE", _days_ago(7))
        if status != "OK":
            return [{"error": "No se pudo buscar"}]

        ids = messages[0].split()
        ids = ids[-max_emails:]  # ultimos N
        results = []

        for mid in ids:
            status, data = mail.fetch(mid, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(data[0][1])
            parsed = _parse_email(msg)
            if parsed and _is_job_related(parsed):
                results.append(parsed)

        mail.logout()
        return sorted(results, key=lambda r: r.get("date", ""), reverse=True)

    except Exception as e:
        return [{"error": str(e)}]


def _parse_email(msg) -> dict | None:
    """Parsea un mensaje de correo a dict."""
    try:
        subject = _decode(msg.get("Subject", ""))
        from_ = _decode(msg.get("From", ""))
        date = msg.get("Date", "")
    except Exception:
        return None

    # Extraer cuerpo
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    break
                except Exception:
                    continue
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception:
            body = ""

    return {
        "subject": subject,
        "from": from_,
        "date": date,
        "body": body[:2000],
        "is_job": False,
    }


def _decode(header_value: str) -> str:
    """Decodifica cabeceras de email."""
    parts = decode_header(header_value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="ignore"))
            except Exception:
                result.append(part.decode("utf-8", errors="ignore"))
        else:
            result.append(str(part))
    return " ".join(result)


def _is_job_related(email_data: dict) -> bool:
    """Determina si un correo esta relacionado con postulaciones."""
    text = (email_data.get("subject", "") + " " + email_data.get("from", "")).lower()

    for kw in _JOB_KEYWORDS:
        if kw in text:
            return True

    for kw in _SENDER_KEYWORDS:
        if kw in text:
            return True

    return False


def _days_ago(days: int) -> str:
    """Retorna fecha en formato IMAP (DD-Mon-YYYY)."""
    from datetime import timedelta
    d = datetime.now(timezone.utc) - timedelta(days=days)
    return d.strftime("%d-%b-%Y")


def summarize(results: list[dict]) -> str:
    """Genera un resumen legible de los correos encontrados."""
    if not results:
        return "No se encontraron correos de postulaciones en los ultimos 7 dias."

    lines = [f"Correos de postulaciones encontrados: {len(results)}"]
    for r in results:
        lines.append(f"\n- {r.get('date', '?')}")
        lines.append(f"  De: {r.get('from', '?')}")
        lines.append(f"  Asunto: {r.get('subject', '?')}")
    return "\n".join(lines)
