#!/usr/bin/env python3
"""
ProGym — send a quote PDF via Gmail SMTP.

Usage:
    python3 send_quote.py <to_email> <pdf_path> <client_name> <metros> <espacio> <objetivo> <nivel>

Credentials are read from a .env file in the repo root (GMAIL_USER / GMAIL_APP_PASSWORD).
"""

import os, sys, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

# ── Load .env from repo root ─────────────────────────────────────────────────
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

GMAIL_USER     = os.environ["GMAIL_USER"]
GMAIL_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 587


def send_quote(to_email: str, pdf_path: str, client_name: str,
               metros: str, espacio: str, objetivo: str, nivel: str) -> None:
    subject = "Tu propuesta personalizada de gimnasio en casa — ProGym"

    plain = f"""Hola {client_name},

Te adjuntamos tu propuesta personalizada de equipamiento para tu gimnasio en casa.

Hemos seleccionado los productos que mejor se adaptan a tu espacio ({metros} m², {espacio}),
tu objetivo ({objetivo}) y tu nivel ({nivel}).

El presupuesto incluye un 12% de descuento. Es válido durante 30 días.

Si tienes alguna pregunta o quieres ajustar la selección, responde a este correo o
llámanos al +34 93 271 27 91.

¡A entrenar!
El equipo de ProGym

──────────────────────────────────────────
ProGym Equipment International, S.L.
C/ Muntaner 499, entlo 4 · 08022 Barcelona
info@progym.es · +34 93 271 27 91
"""

    html = f"""<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#1A1A1A;max-width:600px;margin:0 auto">
<div style="background:#000;padding:16px 24px;border-radius:4px 4px 0 0">
  <img src="https://raw.githubusercontent.com/CescVilanova/gym-recommender/main/assets/logo_transparent.png"
       alt="ProGym" height="34" style="display:block"/>
</div>
<div style="padding:28px 24px">
  <p>Hola <strong>{client_name}</strong>,</p>
  <p>Te adjuntamos tu propuesta personalizada de equipamiento para tu <strong>gimnasio en casa</strong>.</p>
  <p>Hemos seleccionado los productos que mejor se adaptan a tu espacio
     (<strong>{metros} m², {espacio}</strong>), tu objetivo
     (<strong>{objetivo}</strong>) y tu nivel (<strong>{nivel}</strong>).</p>
  <p>El presupuesto incluye un <strong style="color:#E8450A">12% de descuento</strong>.
     Es válido durante <strong>30 días</strong>.</p>
  <p>Si tienes alguna pregunta o quieres ajustar la selección, responde a este correo
     o llámanos al <strong>+34 93 271 27 91</strong>.</p>
  <p style="color:#E8450A;font-weight:bold">¡A entrenar!</p>
  <p>El equipo de ProGym</p>
</div>
<div style="background:#1A1A1A;color:#AAA;font-size:11px;padding:14px 24px;border-radius:0 0 4px 4px">
  ProGym Equipment International, S.L. · C/ Muntaner 499, entlo 4 · 08022 Barcelona<br>
  info@progym.es · +34 93 271 27 91 · ES B66634700
</div>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["From"]    = GMAIL_USER
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))

    # Attach PDF
    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition",
                    f'attachment; filename="{Path(pdf_path).name}"')
    msg_with_attachment = MIMEMultipart("mixed")
    msg_with_attachment["From"]    = GMAIL_USER
    msg_with_attachment["To"]      = to_email
    msg_with_attachment["Subject"] = subject
    msg_with_attachment.attach(msg)
    msg_with_attachment.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg_with_attachment.as_string())

    print(f"✓ Email sent to {to_email} with attachment {Path(pdf_path).name}")


if __name__ == "__main__":
    if len(sys.argv) != 8:
        print("Usage: send_quote.py <to> <pdf> <client_name> <metros> <espacio> <objetivo> <nivel>")
        sys.exit(1)
    send_quote(*sys.argv[1:])
