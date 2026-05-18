"""Enrich area_protegida.geojson with visit totals from local CSVs (matched by name).
Writes area_protegida_enriched.geojson with extra props csv_name and visits_total.
"""
import json, csv, os, unicodedata, re

BASE = r"C:\Users\maxx\Downloads\Nueva carpeta"
SRC  = os.path.join(BASE, "area_protegida.geojson")
OUT  = os.path.join(BASE, "area_protegida_enriched.geojson")

# Sum visits per park name from CSVs
visits_total = {}
files = [
    ("parques_misiones.csv",  "area_protegida"),
    ("gran_parque_ibera.csv", "area_protegida"),
    ("parques_chubut.csv",    "area_protegida"),
    ("parque_ischigualasto.csv", None),
]
for fn, col in files:
    p = os.path.join(BASE, fn)
    if not os.path.exists(p): continue
    with open(p, encoding="utf-8") as h:
        for row in csv.DictReader(h):
            v = row.get("visitas", "")
            if v in ("", "NA", None): continue
            try: n = int(v)
            except ValueError: continue
            name = (row.get(col) if col else "Ischigualasto") or ""
            name = name.strip()
            if name:
                visits_total[name] = visits_total.get(name, 0) + n
print("CSV totals:", visits_total)

def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()

# Explicit, distinctive patterns per CSV name. Each must match the full feature name.
CSV_PATTERNS = [
    ("Reducciones Jesuiticas",            r"misiones jesu|reducciones jesu"),
    ("Parque Provincial Salto Encantado", r"salto encantado"),
    ("Parque Provincial Mocona",          r"\bmocona\b"),
    ("Parque Tematico de la Cruz",        r"tematic.*cruz|cruz.*tematic"),
    ("Espectaculo de Imagen y Sonido",    r"imagen y sonido"),
    ("Iberá",                             r"\bibera\b"),
    ("Ischigualasto",                     r"ischigualasto"),
    ("Península Valdés",                  r"peninsula valdes|valdes.*peninsula|humedales peninsula de valdes"),
    ("Punta Tombo",                       r"punta tombo"),
    ("Punta Loma",                        r"punta loma"),
    ("Punta Marqués",                     r"punta marques"),
    ("Cabo Dos Bahías",                   r"cabo dos bahias|cabo dos bahias"),
    ("Bosque Petrificado Sarmiento",      r"bosque petrificado sarmiento"),
]
# Normalize CSV-name keys so they match what's in visits_total (which uses CSV spellings).
def find_visits(csv_label):
    n = norm(csv_label)
    for orig, v in visits_total.items():
        if norm(orig) == n: return orig, v
    return None, 0

g = json.load(open(SRC, encoding="utf-8"))
matched = 0
for feat in g["features"]:
    p = feat["properties"]
    p["display_name"] = p.get("fna") or p.get("gna") or p.get("nam") or "Área protegida"
    name_n = norm(p.get("fna","") + " " + p.get("nam",""))
    for label, pat in CSV_PATTERNS:
        if re.search(pat, name_n):
            orig, v = find_visits(label)
            p["csv_name"] = orig or label
            p["visits_total"] = v
            matched += 1
            break
    for k in ("gid","entidad","objeto"):
        p.pop(k, None)

print(f"features: {len(g['features'])}, matched to CSVs: {matched}")
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(g, f, ensure_ascii=False, separators=(",", ":"))
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
