"""Sentinel-2 cloud-free mosaic (Copernicus free & open) — via a STAC search.

Builds a *simplified* low-cloud mosaic: searches the open Element-84 earth-search
STAC for Sentinel-2 L2A scenes over Cameroon, keeps the least-cloudy scene per
MGRS tile, mosaics their ``visual`` (true-colour) COGs through GDAL's
``/vsicurl/`` reader, clips to the boundary, and writes a COG.

A true seamless cloud-free composite (per-pixel median over a season) is a Phase
3+ refinement; this gives the frontend a real, attributable imagery layer now.
"""
from __future__ import annotations

import _common as c
from catalog.collections import CAMEROON_BBOX, Layer

STAC_API = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
# A recent dry-season window over Cameroon tends to be the least cloudy.
DATE_WINDOW = "2024-11-01/2025-02-28"


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    from pystac_client import Client

    client = Client.open(STAC_API)
    search = client.search(
        collections=[COLLECTION],
        bbox=CAMEROON_BBOX,
        datetime=DATE_WINDOW,
        query={"eo:cloud_cover": {"lt": layer.extra["max_cloud_cover"]}},
        max_items=400,
    )
    items = list(search.items())
    c.log.info("Sentinel-2 candidate scenes: %d", len(items))
    if not items:
        raise RuntimeError("No low-cloud Sentinel-2 scenes for Cameroon in window")

    # Least-cloudy scene per MGRS tile.
    best: dict[str, object] = {}
    for it in items:
        tile = it.properties.get("grid:code") or it.id.split("_")[1]
        cur = best.get(tile)
        if cur is None or it.properties["eo:cloud_cover"] < cur.properties["eo:cloud_cover"]:
            best[tile] = it
    c.log.info("Sentinel-2 tiles selected: %d", len(best))

    # Mosaic the remote `visual` (true-colour) COGs, read in place via /vsicurl/.
    # Cameroon straddles UTM zones 32N and 33N, so we CANNOT use gdalbuildvrt
    # (it locks onto the first tile's CRS and silently drops the other zone).
    # A single gdalwarp reprojects every tile into EPSG:4326 and mosaics them.
    # We cap the output resolution (default ~55 m) so a country-wide RGB mosaic
    # stays a sensible size for a web preview — full 10 m is a Phase 3+ refinement.
    hrefs = [f"/vsicurl/{it.assets['visual'].href}" for it in best.values()]
    cutline = c.cameroon_cutline()
    res = layer.extra.get("target_res_deg", 0.0005)
    clipped = c.WORK_DIR / "sentinel2_cmr.tif"
    c.run([
        "gdalwarp", "-overwrite",
        "-t_srs", "EPSG:4326",
        "-cutline", str(cutline), "-crop_to_cutline",
        "-tr", str(res), str(res),
        "-dstnodata", "0",
        "-multi", "-wo", "NUM_THREADS=ALL_CPUS",
        "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE",
        *hrefs, str(clipped),
    ])
    cog = c.COG_DIR / f"{layer.id}.tif"
    c.to_cog(clipped, cog)

    href = c.upload_cog(cog, key=f"cogs/{layer.id}.tif")
    return c.register(layer, assets={
        "data": {
            "href": href,
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data", "visual"],
            "title": "Sentinel-2 true-colour low-cloud mosaic (COG)",
        },
    }, extra_properties={"geoportal:mosaic_window": DATE_WINDOW})
