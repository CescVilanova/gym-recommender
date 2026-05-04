# ProGym Gym Recommender — Routine Orchestration

Automated mode only. No questions. Process input and deliver result.

---

## Input

The `text` field contains a Formless `all_answers` block, e.g.:
```
tipo_de_proyecto:
Gimnasio en casa

objetivo_principal:
Perder peso, Ganar músculo

presupuesto:
Más de 15.000€

nivel:
intermedio

metros_cuadrados:
24

tipo_de_espacio:
garaje

equipamiento:
un poco de todo

email_para_recibir_la_propuesta:
cliente@email.com
```

Extract `email_para_recibir_la_propuesta` as the delivery address.
Derive `client_name` from the email prefix (e.g. `juan.garcia@...` → `Juan Garcia`). Use `Cliente ProGym` as fallback.

---

## Step 1 — Download repo assets

`reportlab` is already installed by the environment's setup script.
Download the runtime assets:

```python
import urllib.request

BASE = "https://raw.githubusercontent.com/CescVilanova/gym-recommender/main"

files = {
    "/tmp/select_products.py": f"{BASE}/scripts/select_products.py",
    "/tmp/generate_quote.py":  f"{BASE}/scripts/generate_quote.py",
    "/tmp/catalog.csv":        f"{BASE}/catalog.csv",
    "/tmp/progym_logo.png":    f"{BASE}/assets/logo_transparent.png",
}

for dest, url in files.items():
    urllib.request.urlretrieve(url, dest)
```

If any download fails, stop and report the error. Do not proceed with missing files.

---

## Step 3 — Select products

```bash
python3 /tmp/select_products.py '<form_text>' /tmp/catalog.csv
```

This outputs a JSON array of selected items. If the array is empty, email the customer
explaining that no products matched their constraints and ask them to contact ProGym directly.

---

## Step 4 — Generate PDF quote

Build the quote JSON:

```json
{
  "quote_number": "2026<6-digit-random>",
  "date": "<today DD/MM/YYYY>",
  "expiry_date": "<today + 30 days DD/MM/YYYY>",
  "client_name": "<derived in Input step>",
  "client_address": "España",
  "commercial": "Sales Department",
  "items": "<output from Step 3>",
  "notes": "Presupuesto válido 30 días. Precios sujetos a disponibilidad de stock. IVA incluido en precios unitarios."
}
```

Run:

```bash
PROGYM_LOGO=/tmp/progym_logo.png python3 /tmp/generate_quote.py '<quote_json>' /tmp/Presupuesto_ProGym_<client>_<YYYYMMDD>.pdf
```

The PDF path is the attachment for Step 5.

---

## Step 5 — Send via Gmail

Send in Spanish to `email_para_recibir_la_propuesta`:

- **Subject:** `Tu propuesta personalizada de gimnasio en casa — ProGym`
- **Body (plain text or simple HTML):** warm consultative message in Spanish — mention the space (m², tipo de espacio), objectives, total estimated investment with discount, and that the full quote is attached. Sign off as _El equipo de ProGym_.
- **Attachment:** the PDF generated in Step 4

If the PDF generation fails, send the email without an attachment and explain that the team will follow up manually.

---

## Rules

- All output (email body, logs) must be in Spanish.
- Never invent products outside the catalog.
