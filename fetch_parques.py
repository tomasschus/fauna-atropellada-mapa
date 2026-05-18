"""Fetch protected-area polygons for the parks present in the local CSVs
from OpenStreetMap (Overpass) and save as parques.geojson.
"""
import urllib.request, urllib.parse, json, os, csv, unicodedata, re
from collections import defaultdict

BASE = r"C:\Users\maxx\Downloads\Nueva carpeta"
OUT  = os.path.join(BASE, "parques.geojson")

# Names we want to match (lowercase, accent-stripped)
WANTED = [
    # Misiones
    ("Reducciones Jesuíticas", r"misiones jesu[ií]ticas|reducciones"),
    ("Parque Provincial Moconá", r"mocon[áa]"),
    ("Parque Provincial Salto Encantado", r"salto encantado"),
    # Corrientes
    ("Iberá", r"iber[áa]"),
    # San Juan
    ("Parque Provincial Ischigualasto", r"ischigualasto"),
    # Chubut
    ("Península Valdés", r"pen[ií]nsula vald[ée]s|valdes"),
    ("Punta Tombo", r"punta tombo"),
    ("Punta Loma", r"punta loma"),
    ("Punta Marqués", r"punta marqu[ée]s"),
    ("Cabo Dos Bahías", r"cabo dos bah[ií]as"),
    ("Bosque Petrificado Sarmiento", r"bosque petrificado.*(sarmiento|jaramillo|natural)?|sarmiento.*petrificado"),
]

# Simpler regex (Overpass dislikes [áa]-style classes)
regex = "Mocon|Salto Encantado|Misiones Jesu|Iber|Ischigualasto|Vald|Punta Tombo|Punta Loma|Punta Marqu|Cabo Dos Bah|Sarmiento|Petrificado"
q = f'''
[out:json][timeout:240];
area["ISO3166-1"="AR"][admin_level=2]->.ar;
(
  relation["boundary"~"protected_area|national_park"]["name"~"{regex}",i](area.ar);
);
out geom;
'''

data = urllib.parse.urlencode({"data": q}).encode()
req = urllib.request.Request(
    "https://overpass-api.de/api/interpreter",
    data=data,
    headers={"User-Agent": "fauna-map/1.0", "Accept": "application/json"},
    method="POST",
)
print("querying overpass...")
b = urllib.request.urlopen(req, timeout=300).read()
j = json.loads(b)
elements = j.get("elements", [])
print(f"got {len(elements)} relations")

# Convert Overpass relation -> GeoJSON polygon/multipolygon
def rings_from_relation(el):
    outer_segs, inner_segs = [], []
    for m in el.get("members", []):
        if m.get("type") != "way" or "geometry" not in m: continue
        coords = [(g["lon"], g["lat"]) for g in m["geometry"]]
        (outer_segs if m.get("role") in ("outer","") else inner_segs).append(coords)

    def stitch(segs):
        rings = []
        segs = [list(s) for s in segs]
        while segs:
            ring = segs.pop(0)
            changed = True
            while changed and ring[0] != ring[-1]:
                changed = False
                for i, s in enumerate(segs):
                    if s[0] == ring[-1]:
                        ring.extend(s[1:]); segs.pop(i); changed=True; break
                    if s[-1] == ring[-1]:
                        ring.extend(reversed(s[:-1])); segs.pop(i); changed=True; break
                    if s[-1] == ring[0]:
                        ring = s[:-1] + ring; segs.pop(i); changed=True; break
                    if s[0] == ring[0]:
                        ring = list(reversed(s))[:-1] + ring; segs.pop(i); changed=True; break
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            if len(ring) >= 4:
                rings.append(ring)
        return rings

    outers = stitch(outer_segs)
    inners = stitch(inner_segs)
    # Build polygons: one outer per polygon, holes attached if inside
    polys = [[o] for o in outers]
    # Naive: put each inner into first outer whose bbox contains it
    for hole in inners:
        hx = [c[0] for c in hole]; hy = [c[1] for c in hole]
        for p in polys:
            o = p[0]
            ox=[c[0] for c in o]; oy=[c[1] for c in o]
            if min(ox)<=min(hx) and max(ox)>=max(hx) and min(oy)<=min(hy) and max(oy)>=max(hy):
                p.append(hole); break
    return polys

features = []
for el in elements:
    tags = el.get("tags", {}) or {}
    polys = rings_from_relation(el)
    if not polys: continue
    geom = ({"type":"Polygon","coordinates":polys[0]}
            if len(polys)==1 else
            {"type":"MultiPolygon","coordinates":polys})
    name_lc = (tags.get("name","")).lower()
    # Strip accents for matching
    nm = unicodedata.normalize("NFD", name_lc); nm = "".join(c for c in nm if unicodedata.category(c)!="Mn")
    matched = None
    for label, r in WANTED:
        if re.search(r, nm):
            matched = label; break
    features.append({
        "type":"Feature",
        "geometry": geom,
        "properties": {
            "osm_id": el.get("id"),
            "name": tags.get("name"),
            "match": matched,
            "protect_class": tags.get("protect_class"),
            "boundary": tags.get("boundary"),
        }
    })

print(f"features: {len(features)}")
fc = {"type":"FeatureCollection","features":features}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(fc, f, ensure_ascii=False)
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
print("matched labels:", sorted(set(f["properties"]["match"] for f in features if f["properties"]["match"])))
