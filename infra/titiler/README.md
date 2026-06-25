# TiTiler — raster tiles for the COGs

Configured via environment in `docker-compose.yml`. The `exports` volume is
mounted read-only at `/exports`, so TiTiler serves the ingested COGs as local
files (`/exports/cogs/<id>.tif`). When COGs move to Cloudflare R2, TiTiler reads
them by URL instead — no code change, just a different asset href.

The API derives each raster layer's tile URL from its STAC asset and hands it to
the frontend, e.g.:

```
GET /cog/WebMercatorQuad/tilejson.json?url=/exports/cogs/sentinel2-mosaic.tif
GET /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=/exports/cogs/<id>.tif
```

Docs: https://developmentseed.org/titiler/

> Phase 3+ upgrade path: swap to **titiler-pgstac** to render directly from STAC
> items/mosaics once COGs are on object storage.
