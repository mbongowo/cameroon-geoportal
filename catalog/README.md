# catalog/

STAC catalog definitions and helpers for the portal.

The catalog is the single source of truth for what data exists and **under what
license**. Built on [STAC](https://stacspec.org/) via **pgSTAC** (the catalog
lives in the same PostGIS instance) and served through `stac-fastapi` /
`titiler-pgstac` in later phases.

## Mandatory fields

Every STAC **Item** registered here MUST include:

- `license` — SPDX-style id or one of: `public-domain`, `CC-BY-4.0`, `ODbL-1.0`,
  `copernicus-free-open`.
- `properties.attribution` — the ready-to-copy attribution string.

Items missing either field are rejected at ingestion (Phase 2).

## Collections

- `cameroon-open` — Public Domain / CC-BY layers (SRTM, Sentinel-2, WorldCover,
  geoBoundaries, WorldPop).
- `osm-odbl` — **separate** collection for OpenStreetMap (ODbL share-alike).

## Contents (Phase 2 — built)

- `collections.py` — the **single source of truth**: the two collections plus the
  six MVP layers, each with its `license`, ready-to-copy `attribution`, source
  URL, and a `license_confirmed` flag mirroring the verification log.
- `register.py` — `build_item` / `validate_item` enforce the mandatory
  `license` + `attribution` (rejecting anything outside the allowed set), and
  `load_items` upserts validated items into pgSTAC.
- `migrate.py` — installs/upgrades the pinned pgSTAC schema and loads the two
  collections. Run once before ingestion:
  `docker compose run --rm worker python /app/catalog/migrate.py`.

> **Import note:** always import as `catalog.collections` / `catalog.register`
> (dotted). Never put this directory directly on `sys.path` — `collections.py`
> would otherwise shadow Python's standard-library `collections`.
