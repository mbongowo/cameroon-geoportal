"""geoBoundaries ADM0–ADM3 (CC-BY 4.0) — vector boundaries into PostGIS.

Downloads each admin level for Cameroon via the geoBoundaries open API, loads
it into the ``layers`` schema, and registers one STAC item whose assets point
to the per-level GeoJSON sources.
"""
from __future__ import annotations

import _common as c
from catalog.collections import Layer


def _level_geojson_url(iso3: str, level: str) -> str:
    import requests

    meta = requests.get(
        f"https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{level}/",
        timeout=120,
    ).json()
    # Full-resolution geometry; fall back to the simplified one.
    return meta.get("gjDownloadURL") or meta["simplifiedGeometryGeoJSON"]


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    iso3 = layer.extra["iso3"]
    assets: dict[str, dict] = {}
    for level in layer.extra["levels"]:
        url = _level_geojson_url(iso3, level)
        local = c.WORK_DIR / f"geoboundaries_{iso3}_{level}.geojson"
        c.download(url, local)
        table = c.load_vector_to_postgis(
            local, schema="layers", table=f"geoboundaries_{level.lower()}",
        )
        c.log.info("loaded %s -> %s", level, table)
        assets[level.lower()] = {
            "href": url,
            "type": "application/geo+json",
            "roles": ["data"],
            "title": f"geoBoundaries {level} ({iso3})",
            "geoportal:postgis_table": table,
        }

    return c.register(layer, assets=assets, extra_properties={
        "geoportal:admin_levels": layer.extra["levels"],
    })
