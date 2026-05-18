import json, os, sys

BASE = r"C:\Users\maxx\Downloads\Nueva carpeta"
ENTRIES = os.path.join(BASE, "all_entries.json")
PROV    = os.path.join(BASE, "provincias.geojson")
OUT     = os.path.join(BASE, "mapa_calor.html")

SPECIES_KEY = "c8e2f576c4d244cd9b3dad90400cb988_596e95c4d2fdb_5d1ebce132736"

# 1) Extract lat/lng + especie from entries
entries = json.load(open(ENTRIES, encoding="utf-8"))
pts = []
for e in entries:
    ans = e.get("entry", {}).get("answers", {}) or {}
    lat = lng = None
    for v in ans.values():
        a = v.get("answer")
        if isinstance(a, dict) and "latitude" in a and "longitude" in a:
            la, ln = a["latitude"], a["longitude"]
            if isinstance(la, (int, float)) and isinstance(ln, (int, float)) and (la or ln):
                lat, lng = la, ln
                break
    if lat is None:
        continue
    sp = (ans.get(SPECIES_KEY, {}) or {}).get("answer") or ""
    sp = sp.strip() if isinstance(sp, str) else ""
    pts.append([lat, lng, sp])
print(f"entries with coords: {len(pts)} / {len(entries)}")

# 2) Load province polygons, build bbox + ring list
prov = json.load(open(PROV, encoding="utf-8"))
provinces = []
for feat in prov["features"]:
    name = feat["properties"]["provincia"]
    geom = feat["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    rings = []  # list of (outer_ring, holes)
    for poly in polys:
        outer = poly[0]
        holes = poly[1:]
        rings.append((outer, holes))
    xs = [c[0] for poly in polys for ring in poly for c in ring]
    ys = [c[1] for poly in polys for ring in poly for c in ring]
    provinces.append({
        "name": name,
        "bbox": (min(xs), min(ys), max(xs), max(ys)),
        "rings": rings,
    })

def point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi):
            inside = not inside
        j = i
    return inside

def find_province(lat, lng):
    x, y = lng, lat
    for p in provinces:
        minx, miny, maxx, maxy = p["bbox"]
        if x < minx or x > maxx or y < miny or y > maxy:
            continue
        for outer, holes in p["rings"]:
            if point_in_ring(x, y, outer) and not any(point_in_ring(x, y, h) for h in holes):
                return p["name"]
    return None

# 3) Assign province
tagged = []
counts = {}
species_counts = {}
for lat, lng, sp in pts:
    pr = find_province(lat, lng)
    tagged.append([round(lat, 6), round(lng, 6), pr, sp])
    counts[pr] = counts.get(pr, 0) + 1
    if sp:
        species_counts[sp] = species_counts.get(sp, 0) + 1

print("province counts:")
for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {k!r:30s} {v}")
print(f"unique species: {len(species_counts)} (top 5: {sorted(species_counts.items(), key=lambda x:-x[1])[:5]})")

prov_names = sorted({t[2] for t in tagged if t[2]})
species_names = sorted(species_counts.keys(), key=lambda s: (-species_counts[s], s.lower()))

# 4) Write HTML
points_json   = json.dumps(tagged, ensure_ascii=False, separators=(",", ":"))
provs_json    = json.dumps(prov_names, ensure_ascii=False)
species_json  = json.dumps([[s, species_counts[s]] for s in species_names], ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Mapa de calor - Fauna atropellada Argentina</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  html, body { margin:0; padding:0; height:100%; font-family: system-ui, sans-serif; }
  #map { position:absolute; top:0; left:0; right:0; bottom:0; }
  #panel {
    position:absolute; top:12px; right:12px; z-index:1000;
    background:#fff; padding:12px 14px; border-radius:8px;
    box-shadow:0 2px 8px rgba(0,0,0,.2); min-width:260px; max-width:300px;
    font-size:13px;
  }
  #panel h1 { font-size:14px; margin:0 0 8px; }
  #panel label { display:block; font-size:12px; color:#555; margin:8px 0 4px; }
  #panel select, #panel input { width:100%; padding:6px; font-size:13px; box-sizing:border-box; }
  #stats { margin-top:10px; font-size:12px; color:#333; }
  #clear { margin-top:8px; width:100%; padding:6px; font-size:12px; cursor:pointer; }
  .badge { display:inline-block; padding:2px 6px; border-radius:4px; background:#eee; }
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <h1>Atropellamientos de fauna</h1>
  <label for="prov">Provincia</label>
  <select id="prov">
    <option value="__all__">Todas (__TOTAL__)</option>
    __PROV_OPTIONS__
  </select>
  <label for="sp">Especie (escribí para buscar)</label>
  <input list="sp_list" id="sp" placeholder="Todas las especies" autocomplete="off">
  <datalist id="sp_list">__SP_OPTIONS__</datalist>
  <button id="clear">Limpiar filtros</button>
  <div id="stats"></div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<script>
const POINTS  = __POINTS__;   // [lat, lng, province, species]
const SPECIES = __SPECIES__;  // [[name, count], ...]
const SP_SET  = new Set(SPECIES.map(s => s[0].toLowerCase()));

const map = L.map('map', { preferCanvas:true }).setView([-38.5, -63.5], 5);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap &copy; CARTO',
  subdomains: 'abcd', maxZoom: 19
}).addTo(map);

let heat = null;
function render() {
  const prov = document.getElementById('prov').value;
  const spRaw = document.getElementById('sp').value.trim();
  const spLc = spRaw.toLowerCase();
  const spExact = SP_SET.has(spLc);

  let filtered = POINTS;
  if (prov !== '__all__') filtered = filtered.filter(p => p[2] === prov);
  if (spRaw) {
    filtered = spExact
      ? filtered.filter(p => p[3].toLowerCase() === spLc)
      : filtered.filter(p => p[3].toLowerCase().includes(spLc));
  }

  const data = filtered.map(p => [p[0], p[1], 1]);
  if (heat) map.removeLayer(heat);
  heat = L.heatLayer(data, { radius: 18, blur: 22, maxZoom: 10, minOpacity: 0.25 }).addTo(map);

  document.getElementById('stats').innerHTML =
    '<span class="badge">' + data.length.toLocaleString('es-AR') + '</span> registros'
    + (spRaw ? ' &middot; especie: <b>' + spRaw + '</b>' : '');

  if (data.length && (prov !== '__all__' || spRaw)) {
    const lats = data.map(d=>d[0]), lngs = data.map(d=>d[1]);
    map.fitBounds([[Math.min(...lats), Math.min(...lngs)], [Math.max(...lats), Math.max(...lngs)]],
                  { padding:[40,40], maxZoom: 11 });
  } else if (prov === '__all__' && !spRaw) {
    map.setView([-38.5, -63.5], 5);
  }
}

document.getElementById('prov').addEventListener('change', render);
let spT;
document.getElementById('sp').addEventListener('input', () => {
  clearTimeout(spT); spT = setTimeout(render, 200);
});
document.getElementById('clear').addEventListener('click', () => {
  document.getElementById('prov').value = '__all__';
  document.getElementById('sp').value = '';
  render();
});
render();
</script>
</body>
</html>
"""

prov_options = "\n    ".join(
    f'<option value="{p}">{p} ({counts.get(p,0)})</option>' for p in prov_names
)
def esc(s):
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
sp_options = "".join(
    f'<option value="{esc(s)}">{esc(s)} ({species_counts[s]})</option>' for s in species_names
)
html = (html
        .replace("__TOTAL__", str(len(tagged)))
        .replace("__PROV_OPTIONS__", prov_options)
        .replace("__SP_OPTIONS__", sp_options)
        .replace("__POINTS__", points_json)
        .replace("__SPECIES__", species_json))

open(OUT, "w", encoding="utf-8").write(html)
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
