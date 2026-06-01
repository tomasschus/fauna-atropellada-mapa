FROM nginx:alpine

COPY *.html /usr/share/nginx/html/
COPY data/all_entries.json /usr/share/nginx/html/all_entries.json
COPY data/provincias.geojson /usr/share/nginx/html/provincias.geojson
COPY data/area_protegida_enriched.geojson /usr/share/nginx/html/area_protegida_enriched.geojson
COPY data/parques_misiones.csv /usr/share/nginx/html/parques_misiones.csv
COPY README.md /usr/share/nginx/html/README.md

RUN printf '<!DOCTYPE html>\n<html lang="es"><head><meta charset="utf-8"><title>Fauna atropellada — Argentina</title>\n<style>body{font-family:system-ui,sans-serif;max-width:680px;margin:40px auto;padding:0 20px;color:#222;line-height:1.5}h1{font-size:22px}a.card{display:block;padding:16px;margin:12px 0;border:1px solid #ddd;border-radius:8px;text-decoration:none;color:#222}a.card:hover{background:#f5f5f5}a.card b{display:block;font-size:16px;margin-bottom:4px;color:#2980b9}.foot{color:#666;font-size:13px;margin-top:24px}</style></head><body>\n<h1>Red Argentina de Monitoreo de Fauna Atropellada</h1>\n<p>10.247 registros de atropellamientos extraídos de Epicollect5.</p>\n<a class="card" href="/mapa_calor.html"><b>Mapa de calor</b>Heatmap nacional con filtro por provincia y especie (10.153 puntos con GPS).</a>\n<a class="card" href="/visitas_vs_accidentes.html"><b>Visitas a parques vs atropellamientos (Misiones)</b>Cruce mensual de visitantes a áreas protegidas y atropellamientos.</a>\n<a class="card" href="/dashboard.html"><b>Dashboard analítico</b>KPIs, serie temporal, top especies, heatmap día×mes y exportación CSV con filtros.</a>\n<a class="card" href="/ecoruta_presentacion.html"><b>EcoRuta Interactiva — Presentación</b>Propuesta de plataforma colaborativa con IA para monitoreo y mitigación de atropellamientos.</a>\n<a class="card" href="/ecoruta_app.html"><b>EcoRuta Interactiva — App demo</b>Demo de la app de reporte ciudadano con mapa, formulario guiado e identificación por foto.</a>\n<p class="foot">Repo: <a href="https://github.com/tomasschus/fauna-atropellada-mapa">github.com/tomasschus/fauna-atropellada-mapa</a></p>\n</body></html>\n' > /usr/share/nginx/html/index.html

RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  index index.html;\n  gzip on;\n  gzip_types application/json application/geo+json text/html text/css application/javascript text/csv;\n  location / { try_files $uri $uri/ =404; }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
