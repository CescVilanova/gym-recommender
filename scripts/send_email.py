#!/usr/bin/env python3
"""
ProGym Email Sender
Sends a PDF quote via Resend API (HTTPS) with attachment.

Required env vars:
  RESEND_API_KEY  — API key from resend.com (free tier: 100 emails/day)
  EMAIL_FROM      — Verified sender address in Resend (e.g. sales@progym.es)
                    For testing, use "onboarding@resend.dev" with your own address as TO

Usage:
  python3 send_email.py <to_address> <pdf_path> <quote_number> \
      <client_name> <space_m2> <space_type> <objective> <nivel> <total_str>
"""

import os, sys, json, base64
import urllib.request, urllib.error
from pathlib import Path

RESEND_API_URL = "https://api.resend.com/emails"

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

    api_key  = os.environ.get("RESEND_API_KEY")
    from_addr = os.environ.get("EMAIL_FROM", "ProGym <onboarding@resend.dev>")

    if not api_key:
        raise EnvironmentError(
            "Falta RESEND_API_KEY.\n"
            "1. Crea cuenta gratuita en https://resend.com\n"
            "2. Genera un API key en resend.com/api-keys\n"
            "3. Añade RESEND_API_KEY=re_xxxx al archivo .env"
        )

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    ctx = dict(client_name=client_name, space_m2=space_m2, space_type=space_type,
               objective=objective, nivel=nivel, total=total)

    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("ascii")

    payload = {
        "from":    from_addr,
        "to":      [to_address],
        "subject": f"Tu propuesta personalizada de gimnasio en casa — ProGym (#{quote_number})",
        "html":    HTML_TEMPLATE.format(**ctx),
        "text":    PLAIN_TEMPLATE.format(**ctx),
        "attachments": [
            {
                "filename": pdf_path.name,
                "content":  pdf_b64,
            }
        ],
    }

    req = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
        print(f"✓ Email enviado a {to_address} | id={result.get('id')} | adjunto: {pdf_path.name}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Resend API error {e.code}: {body}")


if __name__ == "__main__":
    if len(sys.argv) != 10:
        print("Uso: send_email.py <to> <pdf_path> <quote_num> <client_name> "
              "<space_m2> <space_type> <objective> <nivel> <total>")
        sys.exit(1)
    send_quote(*sys.argv[1:])
