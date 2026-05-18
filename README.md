# Fauna Atropellada — Mapa de calor

Mapa de calor interactivo de atropellamientos de fauna en Argentina, con filtro por provincia y especie, y capa de áreas protegidas.

Datos extraídos de la [Red Argentina de Monitoreo de Fauna Atropellada](https://five.epicollect.net/project/red-argentina-de-monitoreo-de-fauna-atropellada) (Epicollect5).

## Estructura

```
.
├── mapa_calor.html              # visor Leaflet (heatmap + filtros + capa áreas protegidas)
├── visitas_vs_accidentes.html   # cruce mensual visitas vs accidentes (Misiones)
├── Dockerfile                   # nginx:alpine sirviendo HTMLs + data estática
├── data/                        # datasets (CSV + GeoJSON)
│   ├── all_entries.json
│   ├── provincias.geojson
│   ├── area_protegida_enriched.geojson   # 19 features SIB/IGN matcheados a CSVs (~370 KB)
│   ├── parques_misiones.csv
│   ├── parques_chubut.csv
│   ├── parque_ischigualasto.csv
│   ├── gran_parque_ibera.csv
│   └── novedades.csv
└── scripts/
    ├── fetch_epicollect.py      # pagina la API y baja todas las entries
    ├── build_map.py             # genera mapa_calor.html
    ├── build_visitas.py         # genera visitas_vs_accidentes.html
    └── enrich_areas.py          # matchea SIB/IGN con CSVs y genera el geojson enriquecido
```

## Uso

```bash
python scripts/fetch_epicollect.py   # opcional: re-bajar la data de Epicollect
python scripts/enrich_areas.py       # requiere data/area_protegida.geojson local (no commiteado)
python scripts/build_map.py          # regenerar el HTML principal
python scripts/build_visitas.py      # regenerar el de visitas
```

## Cobertura

10.153 puntos con coordenadas (94 sin GPS). Top provincias: Misiones 7.229, Corrientes 557, Jujuy 452, Buenos Aires 361, Entre Ríos 315.

Fuentes geográficas: SIB/IGN (áreas protegidas, no commiteado por tamaño) · [jazzido/Polymaps-Argentina](https://github.com/jazzido/Polymaps-Argentina) (provincias).
