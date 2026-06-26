"""GHSL built-up surface (CC-BY 4.0) — JRC Global Human Settlement Layer.

A single global GeoTIFF in World Mollweide (EPSG:54009), shipped in a zip. We
download, unzip, reproject + clip to Cameroon (clip_raster_to_cameroon always
warps to EPSG:4326), write a COG, and clean up the ~2 GB of intermediates.
"""
from __future__ import annotations

import shutil
import zipfile

import _common as c
from catalog.collections import Layer


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    zip_path = c.WORK_DIR / f"{layer.id}.zip"
    c.download(layer.extra["zip_url"], zip_path)
    raw = c.WORK_DIR / f"{layer.id}_raw"
    raw.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(raw)
    tif = next(raw.rglob("*.tif"))

    clipped = c.WORK_DIR / f"{layer.id}_cmr.tif"
    c.clip_raster_to_cameroon(tif, clipped, nodata=layer.extra.get("nodata"))
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

    shutil.rmtree(raw, ignore_errors=True)
    clipped.unlink(missing_ok=True)
    zip_path.unlink(missing_ok=True)
    return item
