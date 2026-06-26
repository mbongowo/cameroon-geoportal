"""Generic tiled-raster ingest for EPSG:4326 tiles.

Download a set of tile URLs (skipping 404s), mosaic, clip to Cameroon, write a
COG, register the STAC item (with its titiler render hint), and clean up the
large intermediates. Shared by the direct-URL datasets (Hansen, JRC water) and
by copdem.py (which computes its tile list).
"""
from __future__ import annotations

import shutil

import _common as c
from catalog.collections import Layer


def mosaic_clip_cog(layer: Layer, urls: list[str], *, nodata=None) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    raw = c.WORK_DIR / f"{layer.id}_raw"
    tifs = []
    for i, url in enumerate(urls):
        dest = raw / f"tile_{i:03d}.tif"
        try:
            c.download(url, dest)
            tifs.append(dest)
        except Exception as exc:  # ocean / missing tiles 404 legitimately
            c.log.info("skip tile %s (%s)", url.rsplit("/", 1)[-1], exc)
    if not tifs:
        raise RuntimeError(f"{layer.id}: no tiles fetched")
    c.log.info("%s: %d/%d tiles fetched", layer.id, len(tifs), len(urls))

    vrt = c.WORK_DIR / f"{layer.id}.vrt"
    c.run(["gdalbuildvrt", str(vrt), *map(str, tifs)])
    clipped = c.WORK_DIR / f"{layer.id}_cmr.tif"
    c.clip_raster_to_cameroon(vrt, clipped, nodata=nodata)
    cog = c.COG_DIR / f"{layer.id}.tif"
    c.to_cog(clipped, cog)
    href = c.upload_cog(cog, key=f"cogs/{layer.id}.tif")

    item = c.register(layer, assets={
        "data": {
            "href": href,
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data"],
            "title": layer.title,
        },
    }, extra_properties={"geoportal:render": layer.extra.get("render", "")})

    # Reclaim disk: the raw tiles + intermediates can be large (GBs).
    shutil.rmtree(raw, ignore_errors=True)
    for p in (vrt, clipped):
        p.unlink(missing_ok=True)
    return item


def ingest(layer: Layer) -> dict:
    return mosaic_clip_cog(layer, layer.extra["tile_urls"], nodata=layer.extra.get("nodata"))
