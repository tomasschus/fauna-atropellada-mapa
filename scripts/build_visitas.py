"""Cross visitor counts (parques_misiones.csv, monthly) with roadkill incidents
in Misiones (from all_entries.json) and emit visitas_vs_accidentes.html.
"""
import json, csv, os, math
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
ENTRIES = os.path.join(DATA, "all_entries.json")
PROV    = os.path.join(DATA, "provincias.geojson")
VISITS  = os.path.join(DATA, "parques_misiones.csv")
OUT     = os.path.join(ROOT, "visitas_vs_accidentes.html")

SPECIES_KEY = "c8e2f576c4d244cd9b3dad90400cb988_596e95c4d2fdb_5d1ebce132736"

# ---------- 1) Build province lookup (only need Misiones polygon) ----------
prov = json.load(open(PROV, encoding="utf-8"))
mis_polys = []
for f in prov["features"]:
    if f["properties"]["provincia"] == "Misiones":
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            mis_polys.append((poly[0], poly[1:]))
xs = [c[0] for outer,_ in mis_polys for c in outer]
ys = [c[1] for outer,_ in mis_polys for c in outer]
MIS_BBOX = (min(xs), min(ys), max(xs), max(ys))

def in_ring(x, y, ring):
    inside = False; n = len(ring); j = n-1
    for i in range(n):
        xi,yi = ring[i]; xj,yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj-xi)*(y-yi)/(yj-yi+1e-18) + xi):
            inside = not inside
        j = i
    return inside

def in_misiones(lat, lng):
    x, y = lng, lat
    mnx,mny,mxx,mxy = MIS_BBOX
    if x<mnx or x>mxx or y<mny or y>mxy: return False
    for outer, holes in mis_polys:
        if in_ring(x,y,outer) and not any(in_ring(x,y,h) for h in holes):
            return True
    return False

# ---------- 2) Accidents per month in Misiones ----------
entries = json.load(open(ENTRIES, encoding="utf-8"))
acc_by_month = defaultdict(int)         # 'YYYY-MM' -> count
total_misiones = 0
for e in entries:
    ans = e.get("entry", {}).get("answers", {}) or {}
    lat = lng = None; date_str = None
    for v in ans.values():
        a = v.get("answer")
        if isinstance(a, dict) and "latitude" in a:
            if isinstance(a.get("latitude"),(int,float)) and isinstance(a.get("longitude"),(int,float)):
                lat, lng = a["latitude"], a["longitude"]
        elif isinstance(a, str) and len(a) >= 10 and a[4] == "-" and a[7] == "-" and date_str is None:
            date_str = a[:10]
    if lat is None or date_str is None: continue
    if not in_misiones(lat, lng): continue
    total_misiones += 1
    acc_by_month[date_str[:7]] += 1
print(f"misiones accidents matched: {total_misiones} across {len(acc_by_month)} months")

# ---------- 3) Visits per month (sum across all areas, ignoring NA) ----------
vis_by_month = defaultdict(int)
vis_by_area  = defaultdict(lambda: defaultdict(int))   # area -> month -> visits
with open(VISITS, encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        d = row["indice_tiempo"][:7]
        v = row["visitas"]
        if v in ("", "NA", None): continue
        try: n = int(v)
        except ValueError: continue
        vis_by_month[d] += n
        vis_by_area[row["area_protegida"]][d] = n
print(f"visit months: {len(vis_by_month)} (areas: {list(vis_by_area.keys())})")

# ---------- 4) Join on month ----------
months = sorted(set(acc_by_month) | set(vis_by_month))
joined = []
for m in months:
    a = acc_by_month.get(m); v = vis_by_month.get(m)
    if a is not None and v is not None and a > 0 and v > 0:
        joined.append({"month": m, "visitas": v, "accidentes": a})
print(f"overlapping months: {len(joined)}  ({joined[0]['month'] if joined else '-'} .. {joined[-1]['month'] if joined else '-'})")

# Pearson correlation
if len(joined) >= 3:
    xs = [j["visitas"] for j in joined]; ys = [j["accidentes"] for j in joined]
    mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    dx2 = sum((x-mx)**2 for x in xs); dy2 = sum((y-my)**2 for y in ys)
    r = num / math.sqrt(dx2*dy2) if dx2 and dy2 else 0.0
    # linear regression y = m*x + b
    slope = num / dx2 if dx2 else 0
    intercept = my - slope*mx
else:
    r = 0; slope = 0; intercept = 0
print(f"Pearson r = {r:.3f}  n = {len(joined)}  slope={slope:.5f}  intercept={intercept:.2f}")

# ---------- 5) HTML ----------
payload = {
    "joined": joined,
    "r": r, "slope": slope, "intercept": intercept,
    "n": len(joined),
    "total_misiones": total_misiones,
}
data_json = json.dumps(payload, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Visitas a parques vs atropellamientos — Misiones</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; padding: 24px; background:#f7f7f8; color:#222; }
  h1 { margin: 0 0 8px; font-size: 20px; }
  .sub { color:#555; margin-bottom: 16px; font-size: 13px; }
  .grid { display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .card { background:#fff; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
  .card h2 { font-size:14px; margin: 0 0 12px; color:#333; }
  .kpis { display:flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
  .kpi { background:#fff; padding:10px 14px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,.08); font-size:13px; }
  .kpi b { display:block; font-size:18px; }
  .neg { color:#c0392b; } .pos { color:#27ae60; }
  canvas { max-width:100%; }
  footer { color:#666; font-size:12px; margin-top:16px; }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
</style></head><body>
<h1>Visitas a parques de Misiones vs atropellamientos de fauna</h1>
<div class="sub">Cruce mensual. Visitas: <code>parques_misiones.csv</code> (5 áreas, sumadas). Atropellamientos: Red Argentina de Monitoreo de Fauna Atropellada, filtrados por point-in-polygon dentro de Misiones.</div>

<div id="kpis" class="kpis"></div>

<div class="grid">
  <div class="card">
    <h2>Serie temporal (doble eje)</h2>
    <canvas id="ts"></canvas>
  </div>
  <div class="card">
    <h2>Dispersión + regresión lineal</h2>
    <canvas id="sc"></canvas>
  </div>
</div>

<footer>Generado a partir de <code>all_entries.json</code> y <code>parques_misiones.csv</code>. Coeficiente de Pearson sobre los meses con ambos datos.</footer>

<script>
const D = __DATA__;

document.getElementById('kpis').innerHTML = `
  <div class="kpi">Meses cruzados <b>${D.n}</b></div>
  <div class="kpi">Atropellamientos en Misiones <b>${D.total_misiones.toLocaleString('es-AR')}</b></div>
  <div class="kpi">Correlación de Pearson <b class="${D.r>=0?'pos':'neg'}">${D.r.toFixed(3)}</b></div>
  <div class="kpi">Pendiente (acc / visita) <b>${D.slope.toExponential(2)}</b></div>
`;

const labels = D.joined.map(d => d.month);
const visitas = D.joined.map(d => d.visitas);
const acc = D.joined.map(d => d.accidentes);

new Chart(document.getElementById('ts'), {
  data: {
    labels,
    datasets: [
      { type:'line', label:'Visitas', data:visitas, borderColor:'#2980b9', backgroundColor:'rgba(41,128,185,.1)', yAxisID:'y1', tension:.25, pointRadius:2 },
      { type:'line', label:'Atropellamientos', data:acc, borderColor:'#c0392b', backgroundColor:'rgba(192,57,43,.1)', yAxisID:'y2', tension:.25, pointRadius:2 },
    ]
  },
  options: {
    interaction: { mode:'index', intersect:false },
    stacked: false,
    scales: {
      y1: { type:'linear', position:'left',  title:{display:true,text:'Visitas'} },
      y2: { type:'linear', position:'right', grid:{drawOnChartArea:false}, title:{display:true,text:'Atropellamientos'} },
    },
  }
});

const minV = Math.min(...visitas), maxV = Math.max(...visitas);
new Chart(document.getElementById('sc'), {
  type: 'scatter',
  data: {
    datasets: [
      { label:'Mes', data: D.joined.map(d=>({x:d.visitas, y:d.accidentes, month:d.month})),
        backgroundColor:'rgba(41,128,185,.7)', pointRadius:5 },
      { type:'line', label:`Regresión (r=${D.r.toFixed(3)})`,
        data:[{x:minV, y: D.slope*minV+D.intercept},{x:maxV, y: D.slope*maxV+D.intercept}],
        borderColor:'#c0392b', borderWidth:2, pointRadius:0, fill:false }
    ]
  },
  options: {
    scales: {
      x: { title:{display:true, text:'Visitas mensuales (todas las áreas)'} },
      y: { title:{display:true, text:'Atropellamientos / mes'} },
    },
    plugins: { tooltip: { callbacks: { label: ctx => {
      const p = ctx.raw;
      return p.month ? `${p.month}: ${p.x.toLocaleString('es-AR')} visitas, ${p.y} acc.` : '';
    }}}}
  }
});
</script>
</body></html>
"""

html = html.replace("__DATA__", data_json)
open(OUT, "w", encoding="utf-8").write(html)
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
