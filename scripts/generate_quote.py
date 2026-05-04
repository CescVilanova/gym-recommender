#!/usr/bin/env python3
"""
ProGym Quote PDF Generator
Matches the ProGym/Odoo presupuesto format.

Usage:
    python3 generate_quote.py '<json_data>' <output_path.pdf>

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
      "description": "Multigimnasio B18 ...",
      "qty": 1,
      "unit_price": 2695.00,
      "discount_pct": 12.0
    }
  ],
  "notes": "Presupuesto válido 30 días."
}

NOTE: unit_price values are IVA-included (PVP). The script computes net amounts
(ex. IVA) for the "Precio Total Desc" column and "Importe base" totals.

The logo is loaded from PROGYM_LOGO env var (defaults to /tmp/progym_logo.png).
If the file doesn't exist, the PDF is generated without a logo (text header only).
"""

import sys
import json
import os
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# ── Brand colors ──────────────────────────────────────────────────────────────
ORANGE     = colors.HexColor('#E8450A')
LIGHT_GRAY = colors.HexColor('#F2F2F2')
MID_GRAY   = colors.HexColor('#CCCCCC')
DARK_GRAY  = colors.HexColor('#555555')
TEXT_BLACK = colors.HexColor('#1A1A1A')

# ── Paths ─────────────────────────────────────────────────────────────────────
LOGO_PATH = os.environ.get('PROGYM_LOGO', '/tmp/progym_logo.png')

# ── Layout constants ──────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN_H       = 18 * mm
HEADER_H       = 28 * mm
MARGIN_BOT     = 22 * mm
CONTENT_W      = PAGE_W - 2 * MARGIN_H
IVA_RATE       = 0.21

COMPANY_INFO = (
    "ProGym Equipment International, S.L.\n"
    "C/ Muntaner 499, entlo 4\n"
    "08022 Barcelona, España\n"
    "ES B66634700"
)
FOOTER_TEXT = "info@progym.es  |  +34 93 271 27 91"


# ── Number formatters ─────────────────────────────────────────────────────────
def _fmt2(v: float) -> str:
    """Always 2 decimal places, European format: 1.234,56"""
    return f"{v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _fmt1(v: float) -> str:
    """1-2 decimal places: strips trailing zero from 2nd decimal."""
    s = f"{v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    if ',' in s:
        dec = s.split(',')[1]
        if len(dec) == 2 and dec[1] == '0':
            s = s[:-1]
    return s


# ── Canvas callbacks (BLACK header band + footer on every page) ──────────────
def _draw_page_chrome(canvas, doc):
    canvas.saveState()

    # Full-width black header band
    canvas.setFillColor(colors.black)
    canvas.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)

    # Logo or text fallback (top-left inside the black band)
    if os.path.exists(LOGO_PATH):
        logo_h = HEADER_H - 10 * mm
        logo_w = logo_h * 3.28
        canvas.drawImage(
            LOGO_PATH,
            MARGIN_H,
            PAGE_H - HEADER_H + 3 * mm,
            width=logo_w,
            height=logo_h,
            preserveAspectRatio=True,
            mask='auto',
        )
    else:
        # Text fallback: "PROGYM" in white/orange
        canvas.setFont('Helvetica-Bold', 18)
        canvas.setFillColor(colors.white)
        canvas.drawString(MARGIN_H, PAGE_H - HEADER_H / 2 - 2, "PRO")
        pro_w = canvas.stringWidth("PRO", 'Helvetica-Bold', 18)
        canvas.setFillColor(ORANGE)
        canvas.drawString(MARGIN_H + pro_w, PAGE_H - HEADER_H / 2 - 2, "GYM")

    # Company info — WHITE, right-aligned inside the black band
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica', 7.5)
    lines = COMPANY_INFO.split('\n')
    y = PAGE_H - 8 * mm
    for line in lines:
        canvas.drawRightString(PAGE_W - MARGIN_H, y, line)
        y -= 9.5

    # Footer
    canvas.setLineWidth(0.3)
    canvas.line(MARGIN_H, MARGIN_BOT - 4 * mm,
                PAGE_W - MARGIN_H, MARGIN_BOT - 4 * mm)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(DARK_GRAY)
    canvas.drawCentredString(PAGE_W / 2, MARGIN_BOT - 10 * mm, FOOTER_TEXT)

    canvas.restoreState()


# ── PDF builder ───────────────────────────────────────────────────────────────
def build_quote(data: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN_H,
        rightMargin=MARGIN_H,
        topMargin=HEADER_H + 8 * mm,
        bottomMargin=MARGIN_BOT,
    )

    story = []

    # Client block (right-aligned)
    client_s = ParagraphStyle(
        'Client', fontName='Helvetica', fontSize=9.5,
        textColor=TEXT_BLACK, leading=14, alignment=TA_RIGHT,
        spaceAfter=4 * mm,
    )
    addr = data.get('client_address', '').replace('\n', '<br/>')
    client_text = f"<b>{data['client_name']}</b>"
    if addr:
        client_text += f"<br/>{addr}"
    story.append(Paragraph(client_text, client_s))

    # Quote title
    title_s = ParagraphStyle(
        'Title', fontName='Helvetica-Bold', fontSize=26,
        textColor=ORANGE, leading=32, spaceAfter=4 * mm,
    )
    story.append(Paragraph(f"Presupuesto # {data['quote_number']}", title_s))

    # Meta row
    story.append(_meta_row(data))
    story.append(Spacer(1, 8 * mm))

    # Items table
    story.append(_items_table(data['items']))
    story.append(Spacer(1, 5 * mm))

    # Totals (kept together on same page)
    story.append(KeepTogether(_totals_block(data['items'])))

    # Notes
    if data.get('notes'):
        story.append(Spacer(1, 6 * mm))
        note_s = ParagraphStyle('Note', fontName='Helvetica', fontSize=7.5,
                                 textColor=DARK_GRAY, leading=11)
        story.append(Paragraph(data['notes'], note_s))

    doc.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    print(f"✓ Quote saved to: {output_path}")


# ── Meta row (fecha / vencimiento / comercial) ────────────────────────────────
def _meta_row(data: dict) -> Table:
    cw = CONTENT_W / 3
    lbl_s = ParagraphStyle('ML', fontName='Helvetica-Bold', fontSize=9,
                            textColor=TEXT_BLACK)
    val_s = ParagraphStyle('MV', fontName='Helvetica', fontSize=9,
                            textColor=DARK_GRAY)

    def cell(label, value):
        return Table([[Paragraph(label, lbl_s)], [Paragraph(value, val_s)]],
                     colWidths=[cw])

    t = Table([[
        cell('Fecha del presupuesto',
             data.get('date', date.today().strftime('%d/%m/%Y'))),
        cell('Vencimiento', data.get('expiry_date', '')),
        cell('Comercial',   data.get('commercial', 'Sales Department')),
    ]], colWidths=[cw, cw, cw])
    t.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


# ── Items table ───────────────────────────────────────────────────────────────
def _items_table(items: list) -> Table:
    DESC_W   = CONTENT_W * 0.32
    UNID_W   = 13 * mm
    DISC_W   = 13 * mm
    remaining = CONTENT_W - DESC_W - UNID_W - DISC_W
    BASE_W        = remaining / 6.4
    PRICE_TDESC_W = BASE_W * 1.4
    PRICE_W       = (remaining - PRICE_TDESC_W) / 5.0

    col_w = [DESC_W, UNID_W,
             PRICE_W, PRICE_W, DISC_W,
             PRICE_W, PRICE_W, PRICE_TDESC_W, PRICE_W]

    hdr_s   = ParagraphStyle('H',  fontName='Helvetica', fontSize=6.5,
                              textColor=DARK_GRAY, leading=8, alignment=TA_CENTER)
    hdr_l_s = ParagraphStyle('HL', fontName='Helvetica', fontSize=6.5,
                              textColor=DARK_GRAY, leading=8)
    hdr_o_s = ParagraphStyle('HO', fontName='Helvetica', fontSize=6.5,
                              textColor=ORANGE, leading=8, alignment=TA_CENTER)
    cell_s  = ParagraphStyle('C',  fontName='Helvetica', fontSize=7.5,
                              textColor=TEXT_BLACK, leading=10)
    num_s   = ParagraphStyle('N',  fontName='Helvetica', fontSize=7.5,
                              textColor=TEXT_BLACK, leading=10, alignment=TA_RIGHT)
    ora_s   = ParagraphStyle('O',  fontName='Helvetica', fontSize=7.5,
                              textColor=ORANGE, leading=10, alignment=TA_RIGHT)

    header_row = [
        Paragraph('Descripción',        hdr_l_s),
        Paragraph('Unid',               hdr_s),
        Paragraph('Precio\nUnidad',     hdr_s),
        Paragraph('Precio\nTotal',      hdr_s),
        Paragraph('Desc.%',             hdr_s),
        Paragraph('Precio U.\nDesc.',   hdr_s),
        Paragraph('Ahorro\nUnidad',     hdr_o_s),
        Paragraph('Precio\nTotal Desc', hdr_s),
        Paragraph('Ahorro\nTotal',      hdr_o_s),
    ]
    table_data = [header_row]

    row_styles = [
        ('LINEBELOW',     (0, 0), (-1, 0), 0.5, MID_GRAY),
        ('TOPPADDING',    (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
    ]

    for idx, item in enumerate(items):
        rn         = idx + 1
        qty        = float(item.get('qty', 1))
        unit_price = float(item.get('unit_price', 0))
        disc_pct   = float(item.get('discount_pct', 0))

        precio_total      = qty * unit_price
        precio_u_desc     = unit_price * (1 - disc_pct / 100)
        ahorro_unidad     = unit_price * disc_pct / 100
        precio_total_desc = qty * unit_price * (1 - disc_pct / 100) \
                            / (1 + IVA_RATE)
        ahorro_total      = qty * unit_price - precio_total_desc

        sku  = item.get('sku', '')
        name = item.get('name', '')
        desc = item.get('description', '')

        full_desc = f"{sku} {name}"
        if desc and desc.strip() and desc.strip() != name.strip():
            short = desc[:120] + ('...' if len(desc) > 120 else '')
            full_desc += f'<br/><font size="6.5" color="#666666">{short}</font>'
        desc_para = Paragraph(full_desc, cell_s)

        row = [
            desc_para,
            Paragraph(f"{_fmt2(qty)} Ud", cell_s),
            Paragraph(_fmt2(unit_price),               num_s),
            Paragraph(_fmt1(precio_total),             num_s),
            Paragraph(_fmt2(disc_pct),                 ora_s),
            Paragraph(_fmt1(precio_u_desc),            num_s),
            Paragraph(_fmt1(ahorro_unidad),            ora_s),
            Paragraph(f"{_fmt2(precio_total_desc)} €", num_s),
            Paragraph(_fmt1(ahorro_total),             ora_s),
        ]
        table_data.append(row)

        bg = LIGHT_GRAY if rn % 2 == 0 else colors.white
        row_styles += [
            ('BACKGROUND',    (0, rn), (-1, rn), bg),
            ('TOPPADDING',    (0, rn), (-1, rn), 8),
            ('BOTTOMPADDING', (0, rn), (-1, rn), 8),
            ('VALIGN',        (0, rn), (-1, rn), 'MIDDLE'),
            ('LINEBELOW',     (0, rn), (-1, rn), 0.3, colors.HexColor('#E8E8E8')),
        ]

    t = Table(table_data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',        (0, 0), (0,  -1), 'LEFT'),
        ('ALIGN',        (1, 0), (-1, -1), 'RIGHT'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        *row_styles,
    ]))
    return t


# ── Totals block ──────────────────────────────────────────────────────────────
def _totals_block(items: list) -> Table:
    importe_base = sum(
        float(i.get('qty', 1)) * float(i.get('unit_price', 0))
        * (1 - float(i.get('discount_pct', 0)) / 100)
        / (1 + IVA_RATE)
        for i in items
    )
    iva   = importe_base * IVA_RATE
    total = importe_base + iva

    lbl_s  = ParagraphStyle('TL', fontName='Helvetica',
                             fontSize=8.5, textColor=DARK_GRAY,  alignment=TA_RIGHT)
    val_s  = ParagraphStyle('TV', fontName='Helvetica',
                             fontSize=8.5, textColor=TEXT_BLACK, alignment=TA_RIGHT)
    bold_s = ParagraphStyle('TB', fontName='Helvetica-Bold',
                             fontSize=9,   textColor=TEXT_BLACK, alignment=TA_RIGHT)

    def fmte(v): return f"{_fmt2(v)} €"

    rows = [
        [Paragraph('Importe base', lbl_s),  Paragraph(fmte(importe_base), val_s)],
        [Paragraph('IVA 21%',      lbl_s),  Paragraph(fmte(iva),          val_s)],
        [Paragraph('Total',        bold_s), Paragraph(fmte(total),        bold_s)],
    ]

    t = Table(rows, colWidths=[CONTENT_W - 38 * mm, 38 * mm])
    t.setStyle(TableStyle([
        ('ALIGN',         (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('LINEABOVE',     (0, 2), (-1, 2),  0.5, MID_GRAY),
    ]))
    return t


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 generate_quote.py '<json>' <output.pdf>")
        sys.exit(1)
    data = json.loads(sys.argv[1])
    build_quote(data, sys.argv[2])
