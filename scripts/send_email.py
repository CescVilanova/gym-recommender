#!/usr/bin/env python3
"""
ProGym Email Sender — Gmail API via OAuth2
Sends a PDF quote from cesc@agentstudio.io with PDF attachment.

Requires (in project root):
  credentials.json  — OAuth2 client credentials from Google Cloud Console
  token.json        — refresh token obtained via setup_gmail_auth.py

Usage:
  python3 send_email.py <to_address> <pdf_path> <quote_number> \
      <client_name> <space_m2> <space_type> <objective> <nivel> <total_str>
"""

import os, sys, json, base64, urllib.request, urllib.parse, urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

PROJECT_ROOT   = Path(__file__).parent.parent
CREDENTIALS    = PROJECT_ROOT / "credentials.json"
TOKEN_FILE     = PROJECT_ROOT / "token.json"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
TOKEN_URL      = "https://oauth2.googleapis.com/token"

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


def _refresh_access_token(tokens: dict, creds: dict) -> str:
    data = urllib.parse.urlencode({
        "client_id":     creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": tokens["refresh_token"],
        "grant_type":    "refresh_token",
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read())
    new_access = resp["access_token"]
    tokens["access_token"] = new_access
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
    return new_access


def _get_access_token() -> str:
    if not CREDENTIALS.exists():
        raise FileNotFoundError(f"No se encuentra {CREDENTIALS}")
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"No se encuentra {TOKEN_FILE} — ejecuta el flujo OAuth primero")
    creds  = json.loads(CREDENTIALS.read_text())["installed"]
    tokens = json.loads(TOKEN_FILE.read_text())
    return _refresh_access_token(tokens, creds)


def send_quote(to_address: str, pdf_path: str, quote_number: str,
               client_name: str, space_m2: str, space_type: str,
               objective: str, nivel: str, total: str) -> None:

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    access_token = _get_access_token()
    ctx = dict(client_name=client_name, space_m2=space_m2, space_type=space_type,
               objective=objective, nivel=nivel, total=total)

    # Build MIME message
    msg = MIMEMultipart("mixed")
    msg["To"]      = to_address
    msg["Subject"] = f"Tu propuesta personalizada de gimnasio en casa — ProGym (#{quote_number})"

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(PLAIN_TEMPLATE.format(**ctx), "plain", "utf-8"))
    alt.attach(MIMEText(HTML_TEMPLATE.format(**ctx),  "html",  "utf-8"))
    msg.attach(alt)

    with open(pdf_path, "rb") as f:
        pdf_part = MIMEApplication(f.read(), _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_path.name)
    msg.attach(pdf_part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    payload = json.dumps({"raw": raw}).encode("utf-8")

    req = urllib.request.Request(
        GMAIL_SEND_URL, data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        print(f"✓ Email enviado a {to_address} | id={result.get('id')} | adjunto: {pdf_path.name}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gmail API error {e.code}: {e.read().decode()}")


if __name__ == "__main__":
    if len(sys.argv) != 10:
        print("Uso: send_email.py <to> <pdf_path> <quote_num> <client_name> "
              "<space_m2> <space_type> <objective> <nivel> <total>")
        sys.exit(1)
    send_quote(*sys.argv[1:])
