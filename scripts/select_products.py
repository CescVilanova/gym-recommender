#!/usr/bin/env python3
"""
ProGym Product Selector

Reads catalog CSV + customer form data, applies filtering and ranking logic,
outputs a JSON array of selected items ready for generate_quote.py.

Usage:
    python3 select_products.py '<form_data_text>' <catalog_csv_path>

Output (stdout): JSON array of items
"""

import sys
import json
import csv
import re


# ── Form data parser ──────────────────────────────────────────────────────────

def parse_form_data(text):
    """Parse Formless all_answers block into a dict."""
    data = {}
    current_key = None
    current_value = []

    for line in text.strip().split('\n'):
        line_stripped = line.strip()
        if not line_stripped:
            if current_key and current_value:
                data[current_key] = '\n'.join(current_value).strip()
            current_key = None
            current_value = []
        elif line_stripped.endswith(':') and current_key is None:
            current_key = line_stripped[:-1].strip()
        elif current_key is not None:
            current_value.append(line_stripped)

    if current_key and current_value:
        data[current_key] = '\n'.join(current_value).strip()

    return data


# ── Value parsers ─────────────────────────────────────────────────────────────

def parse_price(price_str):
    if not price_str:
        return 0.0
    cleaned = re.sub(r'[€\s]', '', str(price_str))
    cleaned = cleaned.replace('.', '').replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_float(val):
    try:
        return float(str(val).replace(',', '.').strip())
    except (ValueError, AttributeError):
        return 0.0


# ── Mapping helpers ───────────────────────────────────────────────────────────

BUDGET_MAP = [
    ('30.000',  50000),
    ('15.000',  20000),
    ('10.000',  30000),
    ('5.000',   10000),
    ('1.000',    5000),
    ('1000',     1000),
]

def budget_cap(presupuesto):
    p = presupuesto.lower()
    for key, val in BUDGET_MAP:
        if key in p:
            return val
    return 15000


OBJETIVO_MAP = {
    'perder peso':    'pérdida peso',
    'ganar músculo':  'ganancia muscular',
    'ganar musculo':  'ganancia muscular',
    'salud general':  'salud general',
    'funcional':      'funcional',
    'rehabilitación': 'rehabilitación',
    'rehabilitacion': 'rehabilitación',
}

NIVEL_MAP = {
    'principiante': 'Princ',
    'intermedio':   'Interm',
    'avanzado':     'Avanz',
}

ROL_PRIORITY = {
    'esencial cardio':      0,
    'esencial fuerza':      1,
    'esencial peso libre':  2,
    'complementario':       3,
    'entry cardio':         4,
    'accesorio':            5,
    'almacenamiento':       6,
}

# Always include these regardless of score (negligible cost/footprint)
ALWAYS_INCLUDE = {'VF97660', 'IR97510'}

# Ceiling height assumptions by space type (metres)
CEILING_BY_SPACE = {
    'garaje': 2.8,
    'local':  2.8,
    'exterior': 99,
    'habitación': 2.4,
    'habitacion': 2.4,
    'salón':  2.4,
    'salon':  2.4,
}


# ── Filter helpers ────────────────────────────────────────────────────────────

def espacio_ok(espacio_col, tipo_espacio):
    if not espacio_col:
        return True
    col = espacio_col.lower()
    if 'cualquiera' in col:
        return True
    return tipo_espacio.lower() in col


def nivel_ok(nivel_col, nivel_cliente):
    if not nivel_col:
        return True
    tag = NIVEL_MAP.get(nivel_cliente.lower(), 'Interm')
    return tag in nivel_col


def objetivo_score(objetivos_col, objetivos_cliente):
    if not objetivos_col:
        return 0
    col = objetivos_col.lower()
    score = 0
    for obj in objetivos_cliente:
        tag = OBJETIVO_MAP.get(obj.strip().lower(), '')
        if tag and tag in col:
            score += 1
    return score


# ── Main selection logic ──────────────────────────────────────────────────────

def select_products(form_text, catalog_path):
    form         = parse_form_data(form_text)
    tipo_espacio = form.get('tipo_de_espacio', 'garaje').lower()
    metros       = parse_float(form.get('metros_cuadrados', '24'))
    nivel        = form.get('nivel', 'intermedio').lower()
    presupuesto  = form.get('presupuesto', 'Más de 15.000€')
    objetivos_raw = form.get('objetivo_principal', 'Perder peso, Ganar músculo')
    objetivos    = [o.strip() for o in objetivos_raw.split(',')]
    discount_pct = 12.0

    cap      = budget_cap(presupuesto)
    max_spend = cap * 0.88                          # 12% headroom
    ceiling   = CEILING_BY_SPACE.get(tipo_espacio, 2.5)

    # Load catalog
    with open(catalog_path, encoding='utf-8') as f:
        catalog = list(csv.DictReader(f))

    # Score and hard-filter
    candidates = []
    for row in catalog:
        sku = row.get('Código', '').strip()

        if not espacio_ok(row.get('Espacio ok', ''), tipo_espacio):
            continue
        if not nivel_ok(row.get('Nivel recomendado', ''), nivel):
            continue

        altura_min = parse_float(row.get('Altura mín m *', '0') or '0')
        if altura_min and altura_min > ceiling:
            continue

        price     = parse_price(row.get('PVP estimado (€)', '0'))
        footprint = parse_float(row.get('Footprint uso m² *', '0') or '0')
        rol       = row.get('Rol en setup', '').strip().lower()
        score     = objetivo_score(row.get('Objetivos', ''), objetivos)

        candidates.append({
            'sku':       sku,
            'price':     price,
            'footprint': footprint,
            'rol':       rol,
            'score':     score,
            'row':       row,
        })

    # Sort: always-include first, then by role priority, then score desc, price asc
    def sort_key(c):
        if c['sku'] in ALWAYS_INCLUDE:
            return (-1, 0, 0)
        priority = ROL_PRIORITY.get(c['rol'], 3)
        return (priority, -c['score'], c['price'])

    candidates.sort(key=sort_key)

    # Greedy bundle build
    selected      = []
    total_fp      = 0.0
    total_price   = 0.0

    for c in candidates:
        sku      = c['sku']
        price    = c['price']
        footprint = c['footprint']
        always   = sku in ALWAYS_INCLUDE

        # Skip zero-price items unless always-include
        if price == 0 and not always:
            continue

        new_fp    = total_fp    + footprint
        new_price = total_price + price

        if new_fp > metros and not always:
            continue
        if new_price > max_spend and not always:
            continue

        row = c['row']
        selected.append({
            'sku':          f"[{sku}]",
            'name':         row.get('Título', ''),
            'description':  row.get('Descripción', ''),
            'qty':          1,
            'unit_price':   price,
            'discount_pct': discount_pct,
        })

        total_fp    = new_fp
        total_price = new_price

    return selected


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python3 select_products.py \'<form_data>\' <catalog.csv>',
              file=sys.stderr)
        sys.exit(1)

    result = select_products(sys.argv[1], sys.argv[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
