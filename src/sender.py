"""Envia cartas de presentacion por correo via Gmail SMTP.

Requiere:
- GMAIL_USER en .env
- GMAIL_APP_PASSWORD en .env (App Password de Google)
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path


def send(
    to_email: str,
    subject: str,
    body: str,
    attachment: str | None = None,
) -> dict:
    """Envia un correo desde Gmail."""
    user = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not user or not password:
        return {"error": "Faltan GMAIL_USER o GMAIL_APP_PASSWORD en .env"}

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if attachment:
        path = Path(attachment)
        if path.exists():
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={path.name}")
            msg.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.send_message(msg)
        return {"ok": True, "to": to_email, "subject": subject}
    except Exception as e:
        return {"error": str(e)}
