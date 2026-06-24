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

`run.py` dispatches to the right script. Shared logic (download, clip-to-Cameroon,
COG conversion, PostGIS load, license gate, STAC registration) lives in
`_common.py`. The Cameroon clip mask is geoBoundaries ADM0 (CC-BY 4.0), so even
the cutline is an open layer.

**License gate (in code):** every script calls `ensure_license_cleared(layer)`
before any download. It refuses to run unless the layer's license is marked
confirmed in `catalog/collections.py` — which mirrors the verification log in
[../data-licenses.md](../data-licenses.md). ODbL (OSM) loads into the isolated
`osm_odbl` schema and the separate `osm-odbl` STAC collection.

## Running (inside the worker container — ships GDAL)

```bash
# 1. one-time: install pgSTAC + load the two collections
docker compose run --rm worker python -m catalog.migrate

# 2. ingest one layer, all of them, or just list them
docker compose run --rm worker python /ingest/run.py --layer srtm
docker compose run --rm worker python /ingest/run.py --all
docker compose run --rm worker python /ingest/run.py --list
```

Credentials: **SRTM** needs NASA Earthdata (`EARTHDATA_USERNAME/PASSWORD` in
`.env`). **Sentinel-2** uses the open Element-84 earth-search STAC (no auth).
WorldCover, geoBoundaries, WorldPop and OSM are public (no auth). COGs are
written to the `exports` volume and uploaded to R2 when it is configured.
