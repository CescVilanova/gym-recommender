#!/usr/bin/env python3
"""
ProGym Email Sender
Sends a PDF quote via Gmail SMTP with attachment.

Required env vars:
  GMAIL_SENDER       — the Gmail address used to send (e.g. sales@progym.es)
  GMAIL_APP_PASSWORD — Gmail App Password (16 chars, no spaces)
                       Create at: https://myaccount.google.com/apppasswords

Usage:
  python3 send_email.py <to_address> <pdf_path> <quote_number> \
      <client_name> <space_m2> <space_type> <objective> <nivel> <total_str>
"""

import os, sys, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

HTML_TEMPLATE = """\
<div style="font-family: Arial, sans-serif; color: #1A1A1A; max-width: 600px;">
  <div style="background:#000;padding:20px 30px;border-radius:4px 4px 0 0;">
    <h1 style="color:#E8450A;margin:0;font-size:22px;">ProGym Equipment International</h1>
  </div>
  <div style="padding:30px;background:#f9f9f9;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 4px 4px;">
    <p>Hola {client_name},</p>
    <p>Te adjuntamos tu propuesta personalizada de equipamiento para tu gimnasio en casa.</p>
    <p>Hemos seleccionado los productos que mejor se adaptan a tu espacio
       (<strong>{space_m2} m², {space_type}</strong>),
       tu objetivo (<strong>{objective}</strong>) y tu nivel (<strong>{nivel}</strong>).</p>
    <p>El presupuesto incluye un <strong>12% de descuento</strong>.
       El total con descuento es de <strong>{total}</strong> (IVA incl.).
       Válido durante <strong>30 días</strong>.</p>
    <p>Si tienes alguna pregunta o quieres ajustar la selección, responde a este correo
       o llámanos al <strong>+34 93 271 27 91</strong>.</p>
    <br/>
    <p>¡A entrenar!<br/>
    <strong>El equipo de ProGym</strong><br/>
    <span style="color:#555;">info@progym.es | +34 93 271 27 91</span></p>
    <hr style="border:none;border-top:1px solid #ddd;margin:20px 0;"/>
    <p style="font-size:11px;color:#888;">
      Presupuesto válido 30 días. Precios sujetos a disponibilidad de stock.
      IVA incluido en precios unitarios.
    </p>
  </div>
</div>
"""

PLAIN_TEMPLATE = """\
Hola {client_name},

Te adjuntamos tu propuesta personalizada de equipamiento para tu gimnasio en casa.

Hemos seleccionado los productos que mejor se adaptan a tu espacio ({space_m2} m², {space_type}),
tu objetivo ({objective}) y tu nivel ({nivel}).

El presupuesto incluye un 12% de descuento.
El total con descuento es de {total} (IVA incl.). Válido durante 30 días.

Si tienes alguna pregunta o quieres ajustar la selección, responde a este correo
o llámanos al +34 93 271 27 91.

¡A entrenar!
El equipo de ProGym
info@progym.es | +34 93 271 27 91
"""


def send_quote(to_address: str, pdf_path: str, quote_number: str,
               client_name: str, space_m2: str, space_type: str,
               objective: str, nivel: str, total: str) -> None:

    sender = os.environ.get("GMAIL_SENDER")
    app_pw = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender or not app_pw:
        raise EnvironmentError(
            "Faltan variables de entorno GMAIL_SENDER y/o GMAIL_APP_PASSWORD.\n"
            "Crea una App Password en https://myaccount.google.com/apppasswords\n"
            "y añádela al entorno antes de ejecutar."
        )

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    ctx = dict(client_name=client_name, space_m2=space_m2, space_type=space_type,
               objective=objective, nivel=nivel, total=total)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Tu propuesta personalizada de gimnasio en casa — ProGym (#{quote_number})"
    msg["From"]    = f"ProGym Equipment <{sender}>"
    msg["To"]      = to_address

    msg.attach(MIMEText(PLAIN_TEMPLATE.format(**ctx), "plain", "utf-8"))
    msg.attach(MIMEText(HTML_TEMPLATE.format(**ctx),  "html",  "utf-8"))

    # Re-wrap as mixed to attach PDF
    outer = MIMEMultipart("mixed")
    outer["Subject"] = msg["Subject"]
    outer["From"]    = msg["From"]
    outer["To"]      = msg["To"]
    outer.attach(msg)

    with open(pdf_path, "rb") as f:
        pdf_part = MIMEApplication(f.read(), _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_path.name)
    outer.attach(pdf_part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(sender, app_pw)
        server.sendmail(sender, [to_address], outer.as_string())

    print(f"✓ Email enviado a {to_address} con adjunto {pdf_path.name}")


if __name__ == "__main__":
    if len(sys.argv) != 10:
        print("Uso: send_email.py <to> <pdf_path> <quote_num> <client_name> "
              "<space_m2> <space_type> <objective> <nivel> <total>")
        sys.exit(1)
    send_quote(*sys.argv[1:])
