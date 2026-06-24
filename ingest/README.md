# ingest/

Per-dataset ingestion scripts. Each script (Phase 2) does the same four steps:

1. **Download** the source data.
2. **Clip** to Cameroon's national boundary (GDAL `gdalwarp` / `ogr2ogr`).
3. **Standardize** — reproject; rasters → Cloud-Optimized GeoTIFF (`rio-cogeo`);
   vectors → PostGIS.
4. **Register** as a STAC item with mandatory `license` + `attribution`.

> **Licensing gate:** before any dataset is downloaded, its license page is
> fetched and confirmed (see [../data-licenses.md](../data-licenses.md)). If a
> license is unclear, the dataset is **skipped** and the maintainer is asked.

## Planned scripts (Phase 2)

| Script | Layer | License |
|---|---|---|
| `srtm.py` | SRTM 30 m DEM | Public Domain |
| `sentinel2.py` | Sentinel-2 cloud-free mosaic | Copernicus free & open |
| `worldcover.py` | ESA WorldCover 10 m | CC-BY 4.0 |
| `geoboundaries.py` | geoBoundaries ADM0–ADM3 | CC-BY 4.0 |
| `worldpop.py` | WorldPop population | CC-BY 4.0 |
| `osm_roads.py` | OpenStreetMap roads | ODbL (→ `osm_odbl` schema) |

`run.py --layer <name>` will dispatch to the right script.

## Running (inside the worker container — ships GDAL)

```bash
docker compose run --rm worker python /ingest/run.py --layer srtm
```
