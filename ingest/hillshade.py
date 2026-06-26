"""Hillshade (topographic relief) derived from the Copernicus DEM COG.

A simple, fully-open topographic product: gdaldem hillshade over the DEM COG,
written back as a COG. Requires the DEM layer (``from_cog``) to be ingested
first (it reads /exports/cogs/<from_cog>.tif).
"""
from __future__ import annotations

import _common as c
from catalog.collections import Layer


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    dem = c.COG_DIR / f"{layer.extra['from_cog']}.tif"
    if not dem.exists():
        raise RuntimeError(f"DEM COG {dem} missing — ingest {layer.extra['from_cog']} first")

    hs = c.WORK_DIR / "hillshade.tif"
    c.run([
        "gdaldem", "hillshade", "-compute_edges", "-z", "2",
        "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE",
        str(dem), str(hs),
    ])
    cog = c.COG_DIR / f"{layer.id}.tif"
    c.to_cog(hs, cog)
    hs.unlink(missing_ok=True)
    href = c.upload_cog(cog, key=f"cogs/{layer.id}.tif")

    return c.register(layer, assets={
        "data": {
            "href": href,
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data"],
            "title": layer.title,
        },
    }, extra_properties={"geoportal:render": layer.extra.get("render", "")})
