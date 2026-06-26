"""Sentinel-2 NDVI (vegetation index) — computed from NIR (B08) + Red (B04).

Mirrors the Sentinel-2 mosaic approach: search the open earth-search STAC for the
least-cloud L2A scene per MGRS tile over Cameroon, mosaic the NIR and Red bands
(reading the remote COGs via /vsicurl, reprojected across UTM zones to EPSG:4326
at a capped resolution), then compute NDVI = (NIR - Red) / (NIR + Red).
Copernicus Sentinel-2 data is free, full and open.
"""
from __future__ import annotations

import _common as c
from catalog.collections import CAMEROON_BBOX, Layer

STAC_API = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
DATE_WINDOW = "2024-11-01/2025-02-28"  # dry season = least cloud


def _select_scenes(layer: Layer):
    from pystac_client import Client

    client = Client.open(STAC_API)
    search = client.search(
        collections=[COLLECTION],
        bbox=CAMEROON_BBOX,
        datetime=DATE_WINDOW,
        query={"eo:cloud_cover": {"lt": layer.extra.get("max_cloud_cover", 10)}},
        max_items=400,
    )
    best: dict[str, object] = {}
    for it in search.items():
        tile = it.properties.get("grid:code") or it.id.split("_")[1]
        cur = best.get(tile)
        if cur is None or it.properties["eo:cloud_cover"] < cur.properties["eo:cloud_cover"]:
            best[tile] = it
    return list(best.values())


def _mosaic_band(scenes, asset_key: str, dst, res: float) -> None:
    """Reproject+mosaic one band across all scenes to EPSG:4326, clipped to Cameroon."""
    cutline = c.cameroon_cutline()
    hrefs = [f"/vsicurl/{s.assets[asset_key].href}" for s in scenes]
    c.run([
        "gdalwarp", "-overwrite", "-t_srs", "EPSG:4326",
        "-cutline", str(cutline), "-crop_to_cutline",
        "-tr", str(res), str(res), "-dstnodata", "0",
        "-multi", "-wo", "NUM_THREADS=ALL_CPUS",
        "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE",
        *hrefs, str(dst),
    ])


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    scenes = _select_scenes(layer)
    c.log.info("NDVI: %d least-cloud scenes selected", len(scenes))
    if not scenes:
        raise RuntimeError("no Sentinel-2 scenes for NDVI window")

    res = layer.extra.get("target_res_deg", 0.0005)
    nir = c.WORK_DIR / "ndvi_nir.tif"
    red = c.WORK_DIR / "ndvi_red.tif"
    _mosaic_band(scenes, "nir", nir, res)
    _mosaic_band(scenes, "red", red, res)

    # NDVI = (NIR - Red) / (NIR + Red); mask where both bands are 0 (no data).
    ndvi = c.WORK_DIR / "ndvi_raw.tif"
    c.run([
        "gdal_calc.py", "-A", str(nir), "-B", str(red),
        "--calc=numpy.where((A.astype(numpy.float32)+B.astype(numpy.float32))>0,"
        "(A.astype(numpy.float32)-B.astype(numpy.float32))/"
        "(A.astype(numpy.float32)+B.astype(numpy.float32)),-999)",
        "--outfile", str(ndvi), "--type=Float32", "--NoDataValue=-999", "--overwrite",
    ])

    cog = c.COG_DIR / f"{layer.id}.tif"
    c.to_cog(ndvi, cog)
    for p in (nir, red, ndvi):
        p.unlink(missing_ok=True)
    href = c.upload_cog(cog, key=f"cogs/{layer.id}.tif")

    return c.register(layer, assets={
        "data": {
            "href": href,
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data"],
            "title": layer.title,
        },
    }, extra_properties={
        "geoportal:render": layer.extra.get("render", ""),
        "geoportal:mosaic_window": DATE_WINDOW,
    })
