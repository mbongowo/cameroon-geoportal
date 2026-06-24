"""ESA WorldCover 10 m land cover (CC-BY 4.0) — public AWS bucket, no auth.

WorldCover v200 (2021) is tiled in 3°×3° GeoTIFFs named by their SW corner.
We compute the tiles covering Cameroon, fetch them over HTTPS, mosaic, clip,
and write a COG.
"""
from __future__ import annotations

import math

import _common as c
from catalog.collections import CAMEROON_BBOX, Layer

# Public, anonymous HTTPS endpoint for the WorldCover open-data bucket.
BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"


def _tiles_for_bbox(bbox: list[float]) -> list[str]:
    """3°-grid tile ids (e.g. ``N03E009``) covering ``bbox``."""
    min_x, min_y, max_x, max_y = bbox
    tiles: list[str] = []
    lat = math.floor(min_y / 3) * 3
    while lat <= max_y:
        lon = math.floor(min_x / 3) * 3
        while lon <= max_x:
            ns = "N" if lat >= 0 else "S"
            ew = "E" if lon >= 0 else "W"
            tiles.append(f"{ns}{abs(lat):02d}{ew}{abs(lon):03d}")
            lon += 3
        lat += 3
    return tiles


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    raw_dir = c.WORK_DIR / "worldcover_raw"
    local_tifs = []
    for tile in _tiles_for_bbox(CAMEROON_BBOX):
        url = f"{BASE}/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
        dest = raw_dir / f"{tile}.tif"
        try:
            c.download(url, dest)
            local_tifs.append(dest)
        except Exception as exc:  # ocean tiles legitimately don't exist
            c.log.info("skip tile %s (%s)", tile, exc)
    if not local_tifs:
        raise RuntimeError("No WorldCover tiles fetched for Cameroon")

    vrt = c.WORK_DIR / "worldcover.vrt"
    c.run(["gdalbuildvrt", str(vrt), *map(str, local_tifs)])
    clipped = c.WORK_DIR / "worldcover_cmr.tif"
    c.clip_raster_to_cameroon(vrt, clipped, nodata=0)
    cog = c.COG_DIR / f"{layer.id}.tif"
    c.to_cog(clipped, cog)

    href = c.upload_cog(cog, key=f"cogs/{layer.id}.tif")
    return c.register(layer, assets={
        "data": {
            "href": href,
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data"],
            "title": "ESA WorldCover 10 m land cover (COG)",
        },
    })
