#!/usr/bin/env python3
"""
ProGym Quote HTML Generator

Generates a styled HTML email body from quote JSON.
No external dependencies — stdlib only.

Usage:
    python3 generate_quote.py '<json_data>' <output_path.html>

JSON structure:
{
  "quote_number": "2026000001",
  "date": "08/04/2026",
  "expiry_date": "08/05/2026",
  "client_name": "Nombre Cliente",
  "client_address": "Ciudad\\nPaís",
  "commercial": "Sales Department",
  "items": [
    {
      "sku": "[B18]",
      "name": "Binom Steel Force Multigimnasio B18",
      "description": "Descripción...",
      "qty": 1,
      "unit_price": 2695.00,
      "discount_pct": 12.0
    }
  ],
  "notes": "Presupuesto válido 30 días."
}

NOTE: unit_price is IVA-included (PVP). Totals are computed ex. IVA.
"""

import sys
import json
from datetime import date


IVA_RATE = 0.21
ORANGE   = '#E8450A'


# ── Number formatters ─────────────────────────────────────────────────────────

def fmt(v: float) -> str:
    """European number format: 1.234,56"""
    return f"{v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


# ── HTML builder ──────────────────────────────────────────────────────────────

def build_html(data: dict) -> str:
    items        = data.get('items', [])
    quote_number = data.get('quote_number', '')
    date_str     = data.get('date', date.today().strftime('%d/%m/%Y'))
    expiry_str   = data.get('expiry_date', '')
    commercial   = data.get('commercial', 'Sales Department')
    client_name  = data.get('client_name', '')
    client_addr  = data.get('client_address', '').replace('\n', '<br>')
    notes        = data.get('notes', '')

    # ── Totals ────────────────────────────────────────────────────────────────
    importe_base = sum(
        float(i.get('qty', 1)) * float(i.get('unit_price', 0))
        * (1 - float(i.get('discount_pct', 0)) / 100)
        / (1 + IVA_RATE)
        for i in items
    )
    iva   = importe_base * IVA_RATE
    total = importe_base + iva

    # ── Item rows ─────────────────────────────────────────────────────────────
    rows_html = ''
    for idx, item in enumerate(items):
        qty        = float(item.get('qty', 1))
        unit_price = float(item.get('unit_price', 0))
        disc_pct   = float(item.get('discount_pct', 0))

        pt_desc = qty * unit_price * (1 - disc_pct / 100) / (1 + IVA_RATE)
        ahorro  = qty * unit_price - pt_desc

        sku   = item.get('sku', '')
        name  = item.get('name', '')
        desc  = item.get('description', '')
        short = desc[:100] + ('…' if len(desc) > 100 else '') if desc else ''

        bg = '#F9F9F9' if idx % 2 == 0 else '#FFFFFF'
        rows_html += f"""
        <tr style="background:{bg};">
          <td style="padding:10px 12px;border-bottom:1px solid #EEEEEE;">
            <strong style="font-size:13px;">{sku} {name}</strong><br>
            <span style="font-size:11px;color:#888888;">{short}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #EEEEEE;text-align:center;font-size:13px;">{int(qty)}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #EEEEEE;text-align:right;font-size:13px;">{fmt(unit_price)} €</td>
          <td style="padding:10px 12px;border-bottom:1px solid #EEEEEE;text-align:center;font-size:13px;color:{ORANGE};font-weight:600;">{fmt(disc_pct)}%</td>
          <td style="padding:10px 12px;border-bottom:1px solid #EEEEEE;text-align:right;font-size:13px;font-weight:600;">{fmt(pt_desc)} €</td>
          <td style="padding:10px 12px;border-bottom:1px solid #EEEEEE;text-align:right;font-size:13px;color:{ORANGE};">{fmt(ahorro)} €</td>
        </tr>"""

    notes_html = f"""
        <tr>
          <td colspan="6" style="padding:16px 12px;font-size:11px;color:#999999;border-top:2px solid #EEEEEE;">
            {notes}
          </td>
        </tr>""" if notes else ''

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Presupuesto ProGym #{quote_number}</title>
</head>
<body style="margin:0;padding:0;background:#F4F4F4;font-family:Arial,Helvetica,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F4F4;padding:32px 0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:6px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- HEADER -->
        <tr>
          <td style="background:#000000;padding:24px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="font-size:22px;font-weight:700;color:#FFFFFF;letter-spacing:1px;">PRO<span style="color:{ORANGE};">GYM</span></span><br>
                  <span style="font-size:11px;color:#AAAAAA;">Equipment International</span>
                </td>
                <td align="right" style="font-size:10px;color:#AAAAAA;line-height:18px;">
                  C/ Muntaner 499, entlo 4<br>
                  08022 Barcelona, España<br>
                  ES B66634700<br>
                  info@progym.es · +34 93 271 27 91
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- TITLE + META -->
        <tr>
          <td style="padding:28px 32px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <div style="font-size:28px;font-weight:700;color:{ORANGE};margin-bottom:16px;">
                    Presupuesto #{quote_number}
                  </div>
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding-right:32px;">
                        <div style="font-size:10px;color:#999;text-transform:uppercase;font-weight:700;margin-bottom:3px;">Fecha</div>
                        <div style="font-size:13px;color:#333;">{date_str}</div>
                      </td>
                      <td style="padding-right:32px;">
                        <div style="font-size:10px;color:#999;text-transform:uppercase;font-weight:700;margin-bottom:3px;">Vencimiento</div>
                        <div style="font-size:13px;color:#333;">{expiry_str}</div>
                      </td>
                      <td>
                        <div style="font-size:10px;color:#999;text-transform:uppercase;font-weight:700;margin-bottom:3px;">Comercial</div>
                        <div style="font-size:13px;color:#333;">{commercial}</div>
                      </td>
                    </tr>
                  </table>
                </td>
                <td align="right" style="vertical-align:top;">
                  <div style="font-size:10px;color:#999;text-transform:uppercase;font-weight:700;margin-bottom:3px;">Cliente</div>
                  <div style="font-size:14px;font-weight:700;color:#222;">{client_name}</div>
                  <div style="font-size:12px;color:#666;">{client_addr}</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ITEMS TABLE -->
        <tr>
          <td style="padding:24px 32px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
              <thead>
                <tr style="background:#1A1A1A;">
                  <th style="padding:10px 12px;text-align:left;font-size:11px;color:#AAAAAA;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Producto</th>
                  <th style="padding:10px 12px;text-align:center;font-size:11px;color:#AAAAAA;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Ud</th>
                  <th style="padding:10px 12px;text-align:right;font-size:11px;color:#AAAAAA;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">P. Unidad</th>
                  <th style="padding:10px 12px;text-align:center;font-size:11px;color:{ORANGE};font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Desc.</th>
                  <th style="padding:10px 12px;text-align:right;font-size:11px;color:#AAAAAA;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Total (ex. IVA)</th>
                  <th style="padding:10px 12px;text-align:right;font-size:11px;color:{ORANGE};font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Ahorro</th>
                </tr>
              </thead>
              <tbody>
                {rows_html}
              </tbody>
            </table>
          </td>
        </tr>

        <!-- TOTALS -->
        <tr>
          <td style="padding:0 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="right">
                  <table cellpadding="0" cellspacing="0" style="min-width:240px;">
                    <tr>
                      <td style="padding:8px 12px;font-size:13px;color:#666;">Importe base</td>
                      <td style="padding:8px 12px;font-size:13px;color:#333;text-align:right;">{fmt(importe_base)} €</td>
                    </tr>
                    <tr>
                      <td style="padding:8px 12px;font-size:13px;color:#666;">IVA 21%</td>
                      <td style="padding:8px 12px;font-size:13px;color:#333;text-align:right;">{fmt(iva)} €</td>
                    </tr>
                    <tr style="border-top:2px solid #EEEEEE;">
                      <td style="padding:10px 12px;font-size:15px;font-weight:700;color:#1A1A1A;">Total</td>
                      <td style="padding:10px 12px;font-size:15px;font-weight:700;color:{ORANGE};text-align:right;">{fmt(total)} €</td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        {notes_html}

        <!-- FOOTER -->
        <tr>
          <td style="background:#F8F8F8;padding:20px 32px;border-top:1px solid #EEEEEE;text-align:center;">
            <span style="font-size:11px;color:#AAAAAA;">info@progym.es &nbsp;·&nbsp; +34 93 271 27 91 &nbsp;·&nbsp; progym.es</span>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 generate_quote.py '<json>' <output.html>")
        sys.exit(1)
    data     = json.loads(sys.argv[1])
    html     = build_html(data)
    out_path = sys.argv[2]
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✓ Quote saved to: {out_path}")
