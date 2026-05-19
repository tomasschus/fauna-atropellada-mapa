"""Build dashboard.html — temporal + species + province analytics
over data/all_entries.json. All filtering happens client-side from an
embedded compact records array.
"""
import json, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
ENTRIES = os.path.join(DATA, "all_entries.json")
PROV    = os.path.join(DATA, "provincias.geojson")
OUT     = os.path.join(ROOT, "dashboard.html")

SPECIES_KEY = "c8e2f576c4d244cd9b3dad90400cb988_596e95c4d2fdb_5d1ebce132736"
DATE_KEY    = "c8e2f576c4d244cd9b3dad90400cb988_596e95c4d2fdb_5977a182424e2"

# --- Province polygons (point-in-polygon) ---
prov = json.load(open(PROV, encoding="utf-8"))
provinces = []
for feat in prov["features"]:
    name = feat["properties"]["provincia"]
    geom = feat["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    rings = [(poly[0], poly[1:]) for poly in polys]
    xs = [c[0] for poly in polys for ring in poly for c in ring]
    ys = [c[1] for poly in polys for ring in poly for c in ring]
    provinces.append({"name": name, "bbox": (min(xs),min(ys),max(xs),max(ys)), "rings": rings})

def in_ring(x,y,ring):
    inside=False; n=len(ring); j=n-1
    for i in range(n):
        xi,yi=ring[i]; xj,yj=ring[j]
        if ((yi>y)!=(yj>y)) and (x<(xj-xi)*(y-yi)/(yj-yi+1e-18)+xi):
            inside = not inside
        j=i
    return inside

def find_province(lat, lng):
    x,y = lng, lat
    for p in provinces:
        mnx,mny,mxx,mxy = p["bbox"]
        if x<mnx or x>mxx or y<mny or y>mxy: continue
        for outer, holes in p["rings"]:
            if in_ring(x,y,outer) and not any(in_ring(x,y,h) for h in holes):
                return p["name"]
    return None

# --- Extract records ---
entries = json.load(open(ENTRIES, encoding="utf-8"))
records = []  # [date_iso, province, species]
for e in entries:
    ans = e.get("entry", {}).get("answers", {}) or {}
    # date
    da = (ans.get(DATE_KEY, {}) or {}).get("answer") or ""
    if isinstance(da, str) and len(da) >= 10 and da[4]=="-" and da[7]=="-":
        date_iso = da[:10]
    else:
        ce = e.get("entry", {}).get("created_at", "")
        date_iso = ce[:10] if ce else None
    if not date_iso: continue
    # species
    sp = (ans.get(SPECIES_KEY, {}) or {}).get("answer") or ""
    sp = sp.strip() if isinstance(sp, str) else ""
    # province via gps
    pr = None
    for v in ans.values():
        a = v.get("answer")
        if isinstance(a, dict) and "latitude" in a and "longitude" in a:
            la, ln = a["latitude"], a["longitude"]
            if isinstance(la,(int,float)) and isinstance(ln,(int,float)) and (la or ln):
                pr = find_province(la, ln); break
    records.append([date_iso, pr or "", sp])

print(f"records: {len(records)}")
all_provs = sorted({r[1] for r in records if r[1]})
top_species = [s for s,_ in Counter(r[2] for r in records if r[2]).most_common()]
print(f"provinces: {len(all_provs)}, species: {len(top_species)}")
print(f"date range: {min(r[0] for r in records)} -> {max(r[0] for r in records)}")

records_json = json.dumps(records, ensure_ascii=False, separators=(",",":"))
provs_json   = json.dumps(all_provs, ensure_ascii=False)
species_json = json.dumps(top_species, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>Dashboard — Fauna atropellada</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background:#f7f7f8; color:#222; }
  h1 { margin: 0 0 4px; font-size: 22px; }
  .sub { color:#555; margin-bottom: 16px; font-size: 13px; }
  .filters { background:#fff; border-radius:8px; padding:12px 16px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,.08); display:flex; flex-wrap:wrap; gap:12px; align-items:end; }
  .f { display:flex; flex-direction:column; gap:4px; font-size:12px; }
  .f label { color:#555; }
  .f select, .f input { padding:6px; font-size:13px; border:1px solid #ccc; border-radius:4px; }
  button { padding:7px 14px; font-size:13px; border:1px solid #2980b9; background:#2980b9; color:#fff; border-radius:4px; cursor:pointer; }
  button.sec { background:#fff; color:#2980b9; }
  .kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap:12px; margin-bottom:16px; }
  .kpi { background:#fff; padding:14px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
  .kpi .lbl { font-size:11px; color:#777; text-transform:uppercase; letter-spacing:.04em; }
  .kpi .val { font-size:22px; font-weight:600; margin-top:2px; }
  .kpi .sub2 { font-size:11px; color:#888; margin-top:2px; }
  .grid { display:grid; grid-template-columns: 2fr 1fr; gap:16px; }
  .grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:16px; }
  .card { background:#fff; border-radius:8px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
  .card h2 { font-size:14px; margin:0 0 10px; color:#333; }
  canvas { max-width:100%; }
  .heat { display:grid; grid-template-columns: 60px repeat(12, 1fr); gap:2px; font-size:11px; }
  .heat .h { color:#666; padding:2px; text-align:center; }
  .heat .row-lbl { color:#666; padding:4px 2px; text-align:right; }
  .heat .cell { aspect-ratio:1; border-radius:2px; background:#eee; position:relative; }
  .heat .cell[data-v] { cursor:default; }
  .heat .cell:hover { outline:2px solid #2980b9; }
  footer { color:#666; font-size:12px; margin-top:16px; }
  @media (max-width: 900px) { .grid, .grid2 { grid-template-columns: 1fr; } }
</style></head><body>

<h1>Dashboard de atropellamientos de fauna</h1>
<div class="sub">Panel exploratorio para Vialidad / municipios / ONGs. Filtra por provincia, especie y rango de fechas; exporta el subset.</div>

<div class="filters">
  <div class="f"><label>Provincia</label>
    <select id="prov"><option value="">Todas</option>__PROV_OPT__</select>
  </div>
  <div class="f"><label>Especie (contiene)</label>
    <input list="sp_list" id="sp" placeholder="Todas" autocomplete="off">
    <datalist id="sp_list">__SP_OPT__</datalist>
  </div>
  <div class="f"><label>Desde</label><input type="date" id="from"></div>
  <div class="f"><label>Hasta</label><input type="date" id="to"></div>
  <button id="clear" class="sec">Limpiar</button>
  <button id="csv">Exportar CSV</button>
</div>

<div id="kpis" class="kpis"></div>

<div class="grid">
  <div class="card"><h2>Atropellamientos por mes</h2><canvas id="tsM"></canvas></div>
  <div class="card"><h2>Por d&iacute;a de la semana</h2><canvas id="dow"></canvas></div>
</div>

<div class="grid2">
  <div class="card"><h2>Top 15 especies</h2><canvas id="sp_chart"></canvas></div>
  <div class="card"><h2>Por provincia</h2><canvas id="prov_chart"></canvas></div>
</div>

<div class="card" style="margin-top:16px">
  <h2>Heatmap d&iacute;a-de-semana &times; mes (estacionalidad)</h2>
  <div id="heat" class="heat"></div>
</div>

<footer>Datos: <a href="https://fauna-atropellada.org.ar/">Red Argentina de Monitoreo de Fauna Atropellada</a> &mdash; Generado a partir de <code>data/all_entries.json</code>.</footer>

<script>
const RAW = __RECORDS__;          // [date, province, species]
const ALL_PROV = __PROVS__;
const DOW_LBL = ['Lun','Mar','Mi&eacute;','Jue','Vie','S&aacute;b','Dom'];
const MON_LBL = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];

let charts = {};

function getFilters() {
  return {
    prov: document.getElementById('prov').value,
    sp:   document.getElementById('sp').value.trim().toLowerCase(),
    from: document.getElementById('from').value,
    to:   document.getElementById('to').value,
  };
}
function applyFilters() {
  const f = getFilters();
  return RAW.filter(r => {
    if (f.prov && r[1] !== f.prov) return false;
    if (f.sp   && !r[2].toLowerCase().includes(f.sp)) return false;
    if (f.from && r[0] < f.from) return false;
    if (f.to   && r[0] > f.to)   return false;
    return true;
  });
}

function destroy(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }

function render() {
  const data = applyFilters();

  // KPIs
  const dates = data.map(d => d[0]).sort();
  const sp = {}; const prov = {}; const months = {};
  for (const [d, p, s] of data) {
    if (s) sp[s] = (sp[s]||0)+1;
    if (p) prov[p] = (prov[p]||0)+1;
    const m = d.slice(0,7);
    months[m] = (months[m]||0)+1;
  }
  const topSp = Object.entries(sp).sort((a,b)=>b[1]-a[1])[0];
  const topPr = Object.entries(prov).sort((a,b)=>b[1]-a[1])[0];
  const monthVals = Object.values(months);
  const avgM = monthVals.length ? Math.round(monthVals.reduce((a,b)=>a+b,0)/monthVals.length) : 0;
  document.getElementById('kpis').innerHTML = `
    <div class="kpi"><div class="lbl">Registros</div><div class="val">${data.length.toLocaleString('es-AR')}</div></div>
    <div class="kpi"><div class="lbl">Rango</div><div class="val" style="font-size:14px">${dates[0]||'-'} <small>&rarr;</small> ${dates[dates.length-1]||'-'}</div><div class="sub2">${Object.keys(months).length} meses con datos</div></div>
    <div class="kpi"><div class="lbl">Promedio mensual</div><div class="val">${avgM}</div></div>
    <div class="kpi"><div class="lbl">Especies distintas</div><div class="val">${Object.keys(sp).length}</div></div>
    <div class="kpi"><div class="lbl">Especie m&aacute;s afectada</div><div class="val" style="font-size:14px">${topSp ? topSp[0] : '-'}</div><div class="sub2">${topSp ? topSp[1] + ' casos' : ''}</div></div>
    <div class="kpi"><div class="lbl">Provincia top</div><div class="val" style="font-size:14px">${topPr ? topPr[0] : '-'}</div><div class="sub2">${topPr ? topPr[1] + ' casos' : ''}</div></div>
  `;

  // Time series (monthly)
  const monthsSorted = Object.keys(months).sort();
  destroy('tsM');
  charts.tsM = new Chart(document.getElementById('tsM'), {
    type:'line',
    data:{ labels:monthsSorted, datasets:[{ label:'Casos', data:monthsSorted.map(m=>months[m]), borderColor:'#c0392b', backgroundColor:'rgba(192,57,43,.12)', tension:.25, pointRadius:1, fill:true }] },
    options:{ scales:{ y:{ beginAtZero:true } }, plugins:{ legend:{display:false} } }
  });

  // Day of week
  const dows = [0,0,0,0,0,0,0];
  for (const [d] of data) {
    const dt = new Date(d+'T00:00:00');
    let w = dt.getUTCDay(); // 0=Sun
    w = (w + 6) % 7; // 0=Mon
    dows[w]++;
  }
  destroy('dow');
  charts.dow = new Chart(document.getElementById('dow'), {
    type:'bar',
    data:{ labels:DOW_LBL, datasets:[{ label:'Casos', data:dows, backgroundColor:'#2980b9' }] },
    options:{ scales:{ y:{ beginAtZero:true } }, plugins:{ legend:{display:false} } }
  });

  // Top species
  const topSpArr = Object.entries(sp).sort((a,b)=>b[1]-a[1]).slice(0,15);
  destroy('sp_chart');
  charts.sp_chart = new Chart(document.getElementById('sp_chart'), {
    type:'bar',
    data:{ labels:topSpArr.map(x=>x[0]), datasets:[{ data:topSpArr.map(x=>x[1]), backgroundColor:'#27ae60' }] },
    options:{ indexAxis:'y', scales:{ x:{ beginAtZero:true } }, plugins:{ legend:{display:false} } }
  });

  // Province
  const provArr = Object.entries(prov).sort((a,b)=>b[1]-a[1]);
  destroy('prov_chart');
  charts.prov_chart = new Chart(document.getElementById('prov_chart'), {
    type:'bar',
    data:{ labels:provArr.map(x=>x[0]), datasets:[{ data:provArr.map(x=>x[1]), backgroundColor:'#8e44ad' }] },
    options:{ indexAxis:'y', scales:{ x:{ beginAtZero:true } }, plugins:{ legend:{display:false} } }
  });

  // DoW × Month heatmap
  const grid = Array.from({length:7}, ()=>Array(12).fill(0));
  for (const [d] of data) {
    const dt = new Date(d+'T00:00:00');
    const w = (dt.getUTCDay() + 6) % 7;
    const m = dt.getUTCMonth();
    grid[w][m]++;
  }
  let maxV = 0;
  for (const row of grid) for (const v of row) if (v>maxV) maxV=v;
  const heat = document.getElementById('heat');
  let html = '<div class="h"></div>' + MON_LBL.map(m=>`<div class="h">${m}</div>`).join('');
  for (let w=0; w<7; w++) {
    html += `<div class="row-lbl">${DOW_LBL[w]}</div>`;
    for (let m=0; m<12; m++) {
      const v = grid[w][m];
      const intensity = maxV ? v/maxV : 0;
      const bg = v ? `rgba(192,57,43,${0.15 + intensity*0.85})` : '#f0f0f0';
      html += `<div class="cell" data-v="${v}" style="background:${bg}" title="${DOW_LBL[w]} - ${MON_LBL[m]}: ${v} casos"></div>`;
    }
  }
  heat.innerHTML = html;
}

document.querySelectorAll('#prov, #sp, #from, #to').forEach(el => {
  el.addEventListener(el.tagName==='INPUT' ? 'input' : 'change', () => {
    clearTimeout(window._t); window._t = setTimeout(render, 150);
  });
});
document.getElementById('clear').addEventListener('click', () => {
  ['prov','sp','from','to'].forEach(id => document.getElementById(id).value = '');
  render();
});
document.getElementById('csv').addEventListener('click', () => {
  const data = applyFilters();
  const rows = [['fecha','provincia','especie'], ...data];
  const csv = rows.map(r => r.map(x => `"${String(x).replace(/"/g,'""')}"`).join(',')).join('\\n');
  const blob = new Blob([csv], { type:'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = `atropellamientos_${Date.now()}.csv`; a.click();
});

render();
</script>
</body></html>
"""

prov_options = "".join(f'<option value="{p}">{p}</option>' for p in all_provs)
sp_options   = "".join(f'<option value="{s}">' for s in top_species[:300])
html = (html
        .replace("__PROV_OPT__", prov_options)
        .replace("__SP_OPT__",   sp_options)
        .replace("__RECORDS__",  records_json)
        .replace("__PROVS__",    provs_json))
open(OUT, "w", encoding="utf-8").write(html)
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
