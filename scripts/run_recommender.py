#!/usr/bin/env python3
"""
ProGym Gym Recommender — full pipeline
Parses a Formless submission, selects products, generates PDF, sends email.

Required env vars:
  GMAIL_SENDER       — Gmail address used to send
  GMAIL_APP_PASSWORD — 16-char Gmail App Password (myaccount.google.com/apppasswords)

Usage:
  python3 run_recommender.py '<formless_text>'
"""

import sys, os, csv, io, json, random, subprocess, urllib.request
from datetime import date, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
CATALOG_URL = "https://raw.githubusercontent.com/CescVilanova/gym-recommender/main/catalog.csv"
LOGO_URL    = "https://raw.githubusercontent.com/CescVilanova/gym-recommender/main/assets/logo_transparent.png"
LOGO_PATH   = "/tmp/progym_logo.png"
DISCOUNT    = 12.0
IVA_RATE    = 0.21


# ── Step 1: Parse Formless submission ──────────────────────────────────────

def parse_submission(text: str) -> dict:
    fields = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for sep in (":", "="):
            if sep in line:
                key, _, val = line.partition(sep)
                fields[key.strip().lower().replace(" ", "_")] = val.strip()
                break

    def get(*keys):
        for k in keys:
            v = fields.get(k, "")
            if v:
                return v
        return ""

    email     = get("email_para_recibir_la_propuesta", "email")
    prefix    = email.split("@")[0] if "@" in email else ""
    client_name = prefix.capitalize() if prefix else "Cliente ProGym"

    space_type = get("tipo_de_espacio", "espacio").lower()
    ceil_h = 2.4 if space_type in ("garaje", "local") else 2.2

    return {
        "tipo_proyecto":  get("tipo_de_proyecto"),
        "objetivo":       get("objetivo_principal"),
        "presupuesto_raw":get("presupuesto"),
        "nivel":          get("nivel").lower(),
        "metros":         float(get("metros_cuadrados") or "20"),
        "space_type":     space_type,
        "equipamiento":   get("equipamiento"),
        "email":          email,
        "client_name":    client_name,
        "ceil_h":         ceil_h,
    }


# ── Step 2: Fetch catalog ──────────────────────────────────────────────────

def fetch_catalog() -> list[dict]:
    with urllib.request.urlopen(CATALOG_URL) as r:
        content = r.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    catalog = list(reader)
    if not catalog:
        raise RuntimeError("Catálogo vacío o no descargado — abortando.")

    def parse_pvp(s):
        return float(s.replace("€", "").replace(",", "").strip()) if s.strip() else 0.0

    for p in catalog:
        p["pvp"] = parse_pvp(p["PVP estimado (€)"])
        p["fp"]  = float(p["Footprint uso m² *"]) if p["Footprint uso m² *"].strip() else 0.0
        p["alt"] = float(p["Altura mín m *"])     if p["Altura mín m *"].strip()     else None
    return catalog


# ── Step 3: Map inputs ─────────────────────────────────────────────────────

BUDGET_MAP = {
    "menos de 1.000€":   1_000,
    "1.000€ – 5.000€":   5_000,
    "5.000€ – 10.000€": 10_000,
    "10.000€ – 30.000€":30_000,
    "más de 15.000€":   20_000,
    "más de 30.000€":   50_000,
}
OBJETIVO_MAP = {
    "perder peso":      "pérdida peso",
    "ganar músculo":    "ganancia muscular",
    "salud general":    "salud general",
    "funcional":        "funcional",
    "rehabilitación":   "rehabilitación",
}
NIVEL_MAP = {
    "principiante": "Princ",
    "intermedio":   "Interm",
    "avanzado":     "Avanz",
}


def map_inputs(info: dict) -> dict:
    budget_raw = info["presupuesto_raw"].lower()
    budget_cap = next((v for k, v in BUDGET_MAP.items() if k in budget_raw), 5_000)
    budget_pvp = budget_cap * 0.88

    objetivos_raw = info["objetivo"].lower()
    objetivo_tags = [tag for kw, tag in OBJETIVO_MAP.items() if kw in objetivos_raw]

    nivel_key = NIVEL_MAP.get(info["nivel"], "Interm")

    return {
        "budget_cap":    budget_cap,
        "budget_pvp":    budget_pvp,
        "objetivo_tags": objetivo_tags,
        "nivel_key":     nivel_key,
    }


# ── Step 4: Filter + build bundle ─────────────────────────────────────────

ALWAYS_SKUS = {"VF97660", "IR97510"}

def passes_filters(p: dict, space: str, nivel_key: str, ceil_h: float) -> bool:
    if not p["Código"].strip():
        return False
    eo = p["Espacio ok"].lower()
    if "cualquiera" not in eo and space not in eo:
        return False
    nv = p["Nivel recomendado"].strip()
    if nv and nv != "—" and nivel_key not in nv:
        return False
    if p["alt"] is not None and p["alt"] > ceil_h:
        return False
    return True


def obj_score(p: dict, tags: list[str]) -> int:
    obj = p["Objetivos"].lower()
    return sum(1 for t in tags if t in obj)


def select_products(catalog: list[dict], info: dict, mapped: dict) -> list[dict]:
    space     = info["space_type"]
    nivel_key = mapped["nivel_key"]
    ceil_h    = info["ceil_h"]
    max_fp    = info["metros"]
    budget_pvp= mapped["budget_pvp"]
    tags      = mapped["objetivo_tags"]

    eligible = [p for p in catalog if passes_filters(p, space, nivel_key, ceil_h)]

    # Always-add accessories
    always = [p for p in eligible if p["Código"] in ALWAYS_SKUS]
    pool   = [p for p in eligible if p["Código"] not in ALWAYS_SKUS]

    total_pvp = sum(p["pvp"] for p in always)
    total_fp  = sum(p["fp"]  for p in always)
    selected  = list(always)

    def add(p):
        nonlocal total_pvp, total_fp
        selected.append(p)
        total_pvp += p["pvp"]
        total_fp  += p["fp"]

    def fits(p):
        return (total_pvp + p["pvp"] <= budget_pvp and
                total_fp  + p["fp"]  <= max_fp)

    ROL_ORDER = ["Esencial cardio", "Esencial fuerza", "Esencial peso libre",
                 "Complementario", "Almacenamiento", "Accesorio"]

    def sort_key(p):
        rol  = p["Rol en setup"]
        ridx = ROL_ORDER.index(rol) if rol in ROL_ORDER else 99
        return (ridx, -obj_score(p, tags), p["pvp"])

    for p in sorted(pool, key=sort_key):
        if fits(p):
            add(p)

    return selected


# ── Step 5: Build quote JSON ───────────────────────────────────────────────

def build_quote_data(selected: list[dict], info: dict) -> tuple[dict, str]:
    today     = date.today()
    expiry    = today + timedelta(days=30)
    quote_num = f"2026{random.randint(100000, 999999)}"

    items = [
        {
            "sku":          f"[{p['Código']}]",
            "name":         p["Título"],
            "description":  p["Descripción"],
            "qty":          1,
            "unit_price":   p["pvp"],
            "discount_pct": DISCOUNT,
        }
        for p in selected
    ]

    data = {
        "quote_number":   quote_num,
        "date":           today.strftime("%d/%m/%Y"),
        "expiry_date":    expiry.strftime("%d/%m/%Y"),
        "client_name":    info["client_name"],
        "client_address": "España",
        "commercial":     "Sales Department",
        "items":          items,
        "notes": ("Presupuesto válido 30 días. Precios sujetos a disponibilidad de stock. "
                  "IVA incluido en precios unitarios."),
    }
    return data, quote_num


# ── Step 6: Generate PDF ───────────────────────────────────────────────────

def generate_pdf(quote_data: dict, client_slug: str) -> str:
    if not os.path.exists(LOGO_PATH):
        urllib.request.urlretrieve(LOGO_URL, LOGO_PATH)

    today      = date.today().strftime("%Y%m%d")
    output_pdf = f"/tmp/Presupuesto_ProGym_{client_slug}_{today}.pdf"
    gen_script = SCRIPTS_DIR / "generate_quote.py"

    result = subprocess.run(
        ["python3", str(gen_script), json.dumps(quote_data), output_pdf],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Error generando PDF:\n{result.stderr}")
    print(result.stdout.strip())
    return output_pdf


# ── Step 7: Send email ─────────────────────────────────────────────────────

def send_email(info: dict, mapped: dict, pdf_path: str, quote_num: str,
               total_str: str) -> None:
    send_script = SCRIPTS_DIR / "send_email.py"
    tags_es = ", ".join({
        "pérdida peso":     "Perder peso",
        "ganancia muscular":"Ganar músculo",
        "salud general":    "Salud general",
        "funcional":        "Funcional",
        "rehabilitación":   "Rehabilitación",
    }.get(t, t) for t in mapped["objetivo_tags"]) or info["objetivo"]

    result = subprocess.run(
        [
            "python3", str(send_script),
            info["email"],
            pdf_path,
            quote_num,
            info["client_name"],
            str(int(info["metros"])),
            info["space_type"],
            tags_es,
            info["nivel"],
            total_str,
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Error enviando email:\n{result.stderr}")
    print(result.stdout.strip())


# ── Main ───────────────────────────────────────────────────────────────────

def main(submission_text: str) -> None:
    print("── ProGym Recommender ──────────────────────────────")

    info   = parse_submission(submission_text)
    mapped = map_inputs(info)
    print(f"Cliente:  {info['client_name']} <{info['email']}>")
    print(f"Espacio:  {info['metros']} m², {info['space_type']} (techo {info['ceil_h']} m)")
    print(f"Objetivo: {mapped['objetivo_tags']}  Nivel: {mapped['nivel_key']}")
    print(f"Budget:   {mapped['budget_cap']:,.0f}€ cap  /  {mapped['budget_pvp']:,.0f}€ PVP max")

    catalog  = fetch_catalog()
    selected = select_products(catalog, info, mapped)

    total_pvp  = sum(p["pvp"] for p in selected)
    total_disc = total_pvp * (1 - DISCOUNT / 100)
    total_fp   = sum(p["fp"] for p in selected)
    base       = total_disc / (1 + IVA_RATE)
    total_iva  = total_disc  # PVP ya incluye IVA
    total_str  = f"{total_disc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

    print(f"\nBundle: {len(selected)} productos  |  {total_fp:.1f} m²  |  PVP {total_pvp:,.0f}€  →  {total_disc:,.2f}€ (desc 12%)")

    if total_disc > mapped["budget_cap"]:
        print("⚠️  AVISO: el total supera el presupuesto del cliente.")

    quote_data, quote_num = build_quote_data(selected, info)
    client_slug = info["email"].split("@")[0]
    pdf_path    = generate_pdf(quote_data, client_slug)

    send_email(info, mapped, pdf_path, quote_num, total_str)
    print("── Proceso completado ──────────────────────────────")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 run_recommender.py '<formless_text>'")
        sys.exit(1)
    main(sys.argv[1])
