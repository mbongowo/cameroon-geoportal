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

## Contents (added in Phase 2)

- `collections.py` — collection definitions with license metadata.
- `register.py` — helper to build & validate STAC items before loading to pgSTAC.
