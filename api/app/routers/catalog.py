"""Catalog / search router.

Phase 1: returns the planned MVP layers as a static preview so the frontend has
a contract to build against. Phase 3 replaces this with live pgSTAC search.
Every item MUST carry `license` and `attribution`.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/search", tags=["catalog"])

# Static MVP catalog preview — mirrors data-licenses.md. Replaced by pgSTAC in Phase 3.
MVP_LAYERS = [
    {
        "id": "srtm-30m-dem",
        "title": "SRTM 30 m DEM",
        "theme": "elevation",
        "type": "raster",
        "license": "public-domain",
        "attribution": "Elevation data: NASA SRTM (public domain).",
        "tier": "open",
    },
    {
        "id": "sentinel2-mosaic",
        "title": "Sentinel-2 cloud-free mosaic",
        "theme": "imagery",
        "type": "raster",
        "license": "copernicus-free-open",
        "attribution": "Contains modified Copernicus Sentinel-2 data, processed for the Cameroon Geoportal.",
        "tier": "open",
    },
    {
        "id": "esa-worldcover-10m",
        "title": "ESA WorldCover 10 m",
        "theme": "landcover",
        "type": "raster",
        "license": "CC-BY-4.0",
        "attribution": "© ESA WorldCover project, licensed under CC-BY 4.0.",
        "tier": "open",
    },
    {
        "id": "geoboundaries-adm",
        "title": "geoBoundaries ADM0–ADM3",
        "theme": "boundaries",
        "type": "vector",
        "license": "CC-BY-4.0",
        "attribution": "Administrative boundaries: geoBoundaries (geoboundaries.org), CC-BY 4.0.",
        "tier": "open",
    },
    {
        "id": "worldpop-population",
        "title": "WorldPop population",
        "theme": "population",
        "type": "raster",
        "license": "CC-BY-4.0",
        "attribution": "Population data: WorldPop (worldpop.org), University of Southampton, CC-BY 4.0.",
        "tier": "open",
    },
    {
        "id": "osm-roads",
        "title": "OpenStreetMap roads",
        "theme": "transport",
        "type": "vector",
        "license": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors, ODbL.",
        "tier": "osm-odbl",
    },
]


@router.get("")
def search(theme: str | None = None) -> dict:
    """List catalog layers, optionally filtered by theme."""
    items = MVP_LAYERS
    if theme:
        items = [i for i in items if i["theme"] == theme]
    return {"count": len(items), "items": items}
