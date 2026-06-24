"""SRTM 30 m DEM (public domain) — NASA via earthaccess.

Searches SRTMGL1 v003 granules over Cameroon, mosaics them, clips to the
national boundary, writes a COG, and registers a STAC item.

Requires NASA Earthdata credentials (EARTHDATA_USERNAME / EARTHDATA_PASSWORD,
or a ~/.netrc entry for urs.earthdata.nasa.gov).
"""
from __future__ import annotations

from pathlib import Path

import _common as c
from catalog.collections import CAMEROON_BBOX, Layer


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    import earthaccess

    earthaccess.login(strategy="environment")  # uses EARTHDATA_USERNAME/PASSWORD
    min_x, min_y, max_x, max_y = CAMEROON_BBOX
    results = earthaccess.search_data(
        short_name=layer.extra["earthaccess_short_name"],
        version=layer.extra["earthaccess_version"],
        bounding_box=(min_x, min_y, max_x, max_y),
    )
    c.log.info("SRTM granules found: %d", len(results))
    if not results:
        raise RuntimeError("No SRTM granules returned for Cameroon bbox")

    raw_dir = c.WORK_DIR / "srtm_raw"
    files = earthaccess.download(results, str(raw_dir))
    tifs = [f for f in files if str(f).lower().endswith((".tif", ".hgt"))]

    # Mosaic -> clip -> COG.
    vrt = c.WORK_DIR / "srtm.vrt"
    c.run(["gdalbuildvrt", str(vrt), *map(str, tifs)])
    clipped = c.WORK_DIR / "srtm_cmr.tif"
    c.clip_raster_to_cameroon(vrt, clipped, nodata=-32768)
    cog = c.COG_DIR / f"{layer.id}.tif"
    c.to_cog(clipped, cog)

    href = c.upload_cog(cog, key=f"cogs/{layer.id}.tif")
    return c.register(layer, assets={
        "data": {
            "href": href,
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data"],
            "title": "SRTM 30 m elevation (COG)",
        },
    })
