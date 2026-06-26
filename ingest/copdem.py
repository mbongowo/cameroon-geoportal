"""Copernicus DEM GLO-30 (30 m) — the portal's elevation layer.

SRTM was skipped (Earthdata creds), so this provides the DEM. Tiles are 1°×1°
COGs on the public AWS open-data bucket (anonymous HTTPS, no auth). We compute
the Cameroon tile list, mosaic, clip, and write a COG; ocean tiles 404 and are
skipped. raster_tiles cleans the ~5 GB of raw tiles after the COG is written.
"""
from __future__ import annotations

import math

import raster_tiles
import _common as c
from catalog.collections import CAMEROON_BBOX, Layer

# GLO-30 (30 m). Tile dirs/files use the "COG_10" token; GLO-90 would be "COG_30".
BASE = "https://copernicus-dem-30m.s3.amazonaws.com"


def _tile_urls() -> list[str]:
    min_x, min_y, max_x, max_y = CAMEROON_BBOX
    urls = []
    for lat in range(math.floor(min_y), math.ceil(max_y)):
        for lon in range(math.floor(min_x), math.ceil(max_x)):
            ns = "N" if lat >= 0 else "S"
            ew = "E" if lon >= 0 else "W"
            name = f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"
            urls.append(f"{BASE}/{name}/{name}.tif")
    return urls


def ingest(layer: Layer) -> dict:
    return raster_tiles.mosaic_clip_cog(layer, _tile_urls(), nodata=None)
