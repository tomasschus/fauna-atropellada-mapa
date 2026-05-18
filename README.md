# Fauna Atropellada — Mapa de calor

Mapa de calor interactivo de atropellamientos de fauna en Argentina, con filtro por provincia.

Datos extraídos de la [Red Argentina de Monitoreo de Fauna Atropellada](https://five.epicollect.net/project/red-argentina-de-monitoreo-de-fauna-atropellada) (Epicollect5).

## Archivos

- **`mapa_calor.html`** — Mapa autocontenido (Leaflet + leaflet.heat). Abrir en el navegador.
- **`all_entries.json`** — Dump completo de la API de Epicollect (10.247 entries, ~41 MB).
- **`provincias.geojson`** — Polígonos de provincias argentinas ([jazzido/Polymaps-Argentina](https://github.com/jazzido/Polymaps-Argentina)).
- **`fetch_epicollect.py`** — Pagina la API y baja todas las entries a `epicollect/`.
- **`build_map.py`** — Extrae coordenadas, asigna provincia por point-in-polygon y genera `mapa_calor.html`.

## Uso

```bash
python fetch_epicollect.py   # opcional: re-bajar la data
python build_map.py          # regenerar el HTML
```

## Cobertura

10.153 puntos con coordenadas (94 sin GPS). Top provincias: Misiones 7.229, Corrientes 557, Jujuy 452, Buenos Aires 361, Entre Ríos 315.
