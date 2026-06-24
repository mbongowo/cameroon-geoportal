"""WorldPop population (CC-BY 4.0) — constrained 100 m, resolved via the API.

Uses the WorldPop REST API to resolve the download URL for Cameroon's
constrained population raster, then clips to the boundary and writes a COG.
"""
from __future__ import annotations

import _common as c
from catalog.collections import Layer

# WorldPop REST: constrained individual-countries population (100 m).
API = "https://www.worldpop.org/rest/data/pop/wpgp1km"  # fallback dataset id
CONSTRAINED_API = "https://www.worldpop.org/rest/data/pop/cic2020_100m"


def _resolve_geotiff_url(iso3: str) -> str:
    import requests

    for api in (CONSTRAINED_API, API):
        try:
            data = requests.get(api, params={"iso3": iso3}, timeout=120).json()
            files = data["data"][0]["files"]
            tif = next(f for f in files if str(f).lower().endswith(".tif"))
            c.log.info("WorldPop resolved: %s", tif)
            return tif
        except Exception as exc:  # try the next endpoint
            c.log.info("WorldPop API %s miss (%s)", api, exc)
    raise RuntimeError(f"Could not resolve a WorldPop GeoTIFF for {iso3}")


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    url = _resolve_geotiff_url(layer.extra["iso3"])
    raw = c.WORK_DIR / "worldpop_cmr_raw.tif"
    c.download(url, raw)

    clipped = c.WORK_DIR / "worldpop_cmr.tif"
    c.clip_raster_to_cameroon(raw, clipped, nodata=-99999)
    cog = c.COG_DIR / f"{layer.id}.tif"
    c.to_cog(clipped, cog)

    href = c.upload_cog(cog, key=f"cogs/{layer.id}.tif")
    return c.register(layer, assets={
        "data": {
            "href": href,
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data"],
            "title": "WorldPop population count (COG)",
        },
    })
