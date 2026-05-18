FROM nginx:alpine

COPY mapa_calor.html /usr/share/nginx/html/index.html
COPY mapa_calor.html /usr/share/nginx/html/mapa_calor.html
COPY all_entries.json /usr/share/nginx/html/all_entries.json
COPY provincias.geojson /usr/share/nginx/html/provincias.geojson
COPY README.md /usr/share/nginx/html/README.md

RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  index index.html;\n  gzip on;\n  gzip_types application/json application/geo+json text/html text/css application/javascript;\n  location / { try_files $uri $uri/ =404; }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
