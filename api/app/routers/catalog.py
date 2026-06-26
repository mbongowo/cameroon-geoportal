"""Catalog / search router — live pgSTAC.

Phase 3: replaces the static preview with real pgSTAC search. Each layer is
returned with its mandatory `license` + `attribution` and the tile URLs the
frontend needs (titiler for raster COGs, Martin for PostGIS vectors).

The license/attribution contract is enforced at the edge too: an item missing
either field is never served (it should be impossible — ingestion validates —
but the API refuses to leak a non-compliant item regardless).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app import db
from app.config import settings

router = APIRouter(tags=["catalog"])


# Default titiler render hints per theme (used when an item has no explicit
# geoportal:render). Imagery is RGB and renders natively (no rescale).
_THEME_RENDER = {
    "imagery": "",
    "population": "rescale=0,80&colormap_name=viridis",
    "landcover": "rescale=10,100&colormap_name=gist_earth",
    "elevation": "rescale=0,4000&colormap_name=terrain",
    "topographic": "rescale=0,255",
}


def _raster_tiles(assets: dict, props: dict) -> dict:
    """titiler tilejson for a raster item's COG (read server-side by path).

    The render hint (rescale + colormap) is embedded so the frontend uses the
    URL as-is. Explicit ``geoportal:render`` wins; otherwise a per-theme default.
    """
    href = assets.get("data", {}).get("href", "")
    # file:///exports/cogs/<id>.tif -> /exports/cogs/<id>.tif (titiler's local path)
    path = href.replace("file://", "")
    base = settings.titiler_public_url.rstrip("/")
    render = props.get("geoportal:render")
    if not render:
        render = _THEME_RENDER.get(props.get("theme", ""), "rescale=0,255")
    suffix = f"&{render}" if render else ""
    return {
        "type": "raster",
        "service": "titiler",
        "tilejson": f"{base}/cog/WebMercatorQuad/tilejson.json?url={path}{suffix}",
        "info": f"{base}/cog/info?url={path}",
    }


def _vector_tiles(assets: dict) -> dict:
    """Martin vector sources for each PostGIS table backing the item."""
    base = settings.martin_public_url.rstrip("/")
    sources = []
    for asset in assets.values():
        table = asset.get("geoportal:postgis_table")
        if not table:
            continue
        source_id = table.split(".")[-1]  # Martin publishes by table name
        sources.append({
            "id": source_id,
            "postgis_table": table,
            "tilejson": f"{base}/{source_id}",
            "tiles": f"{base}/{source_id}/{{z}}/{{x}}/{{y}}",
        })
    return {"type": "vector", "service": "martin", "sources": sources}


def _layer_view(feature: dict) -> dict:
    """Project a STAC feature into the compact shape the frontend consumes."""
    props = feature.get("properties", {})
    assets = feature.get("assets", {})
    datatype = props.get("geoportal:datatype")
    collection = feature.get("collection")

    tiles: dict = {}
    if datatype == "raster":
        tiles = _raster_tiles(assets, props)
    elif datatype == "vector":
        tiles = _vector_tiles(assets)

    return {
        "id": feature.get("id"),
        "collection": collection,
        "title": props.get("title"),
        "theme": props.get("theme"),
        "datatype": datatype,
        # license + attribution are mandatory and always surfaced.
        "license": feature.get("license") or props.get("license"),
        "attribution": props.get("attribution"),
        "tier": "osm-odbl" if collection == "osm-odbl" else "open",
        "bbox": feature.get("bbox"),
        "tiles": tiles,
    }


def _compliant(view: dict) -> bool:
    """Never serve an item missing license or attribution."""
    return bool(view.get("license")) and bool(view.get("attribution"))


@router.get("/search")
def search(
    theme: str | None = Query(None),
    collection: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """List catalog layers (live from pgSTAC), optionally filtered."""
    body: dict = {"limit": limit}
    if collection:
        body["collections"] = [collection]
    features = db.search(body).get("features", [])
    items = [_layer_view(f) for f in features]
    if theme:
        items = [i for i in items if i["theme"] == theme]
    items = [i for i in items if _compliant(i)]
    return {"count": len(items), "items": items}


@router.get("/collections")
def collections() -> dict:
    """List STAC collections (the two licensing tiers)."""
    cols = db.all_collections()
    return {
        "collections": [
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "description": c.get("description"),
                "license": c.get("license"),
            }
            for c in cols
        ]
    }


@router.get("/items/{item_id}")
def item(item_id: str) -> dict:
    """Return one layer (compact view + the full STAC item)."""
    feature = db.get_item(item_id)
    if not feature:
        raise HTTPException(status_code=404, detail=f"item {item_id!r} not found")
    view = _layer_view(feature)
    if not _compliant(view):
        raise HTTPException(status_code=409, detail="item missing license/attribution")
    view["stac"] = feature
    return view
