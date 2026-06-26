"""Sentinel-2 by chosen date.

Searches the open Element-84 earth-search STAC for the least-cloudy Sentinel-2
L2A scene near a chosen date over an AOI, and returns a titiler tilejson that
renders that scene's true-colour COG directly (titiler reads the remote COG via
GDAL /vsicurl). Lets users pull live imagery for any date — not just the static
mosaic. Copernicus data is free, full and open.
"""
from __future__ import annotations

import datetime as _dt

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.config import settings

router = APIRouter(tags=["sentinel"])

STAC_SEARCH = "https://earth-search.aws.element84.com/v1/search"
CAMEROON_BBOX = [8.40, 1.65, 16.21, 13.10]


@router.get("/sentinel")
def sentinel_by_date(
    date: str = Query(..., description="Target date YYYY-MM-DD"),
    window_days: int = Query(15, ge=0, le=60),
    max_cloud: int = Query(40, ge=0, le=100),
    bbox: str | None = Query(None, description="minx,miny,maxx,maxy (defaults to Cameroon)"),
) -> dict:
    """Return the least-cloudy Sentinel-2 scene near ``date`` + a titiler tilejson."""
    try:
        target = _dt.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")

    aoi = [float(x) for x in bbox.split(",")] if bbox else CAMEROON_BBOX
    start = target - _dt.timedelta(days=window_days)
    end = target + _dt.timedelta(days=window_days)
    body = {
        "collections": ["sentinel-2-l2a"],
        "bbox": aoi,
        "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        "limit": 10,
    }
    try:
        resp = httpx.post(STAC_SEARCH, json=body, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"STAC search failed: {exc}")

    features = resp.json().get("features", [])
    if not features:
        raise HTTPException(
            status_code=404,
            detail=f"No Sentinel-2 scene < {max_cloud}% cloud within "
                   f"±{window_days} days of {date}",
        )
    scene = features[0]
    visual = scene["assets"].get("visual") or scene["assets"].get("true_color")
    if not visual:
        raise HTTPException(status_code=404, detail="scene has no true-colour asset")

    base = settings.titiler_public_url.rstrip("/")
    url = visual["href"]
    return {
        "scene_id": scene["id"],
        "datetime": scene["properties"]["datetime"],
        "cloud_cover": scene["properties"].get("eo:cloud_cover"),
        "bbox": scene["bbox"],
        "attribution": "Contains modified Copernicus Sentinel-2 data, free and open.",
        "tiles": {
            "type": "raster",
            "service": "titiler",
            "tilejson": f"{base}/cog/WebMercatorQuad/tilejson.json?url={url}",
        },
    }
