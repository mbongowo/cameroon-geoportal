"""Health facilities (healthsites.io, ODbL) — Cameroon point dataset.

healthsites.io is OpenStreetMap-derived, so it lives in the isolated osm_odbl
tier (ODbL share-alike). Downloaded as GeoJSON from HDX.
"""
from __future__ import annotations

import _common as c
from catalog.collections import Layer


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    geojson = c.WORK_DIR / "cameroon_healthsites.geojson"
    c.download(layer.extra["hdx_geojson"], geojson)

    table = c.load_vector_to_postgis(
        geojson, schema="osm_odbl", table=layer.extra["table"], promote_multi=False,
    )
    c.log.info("loaded health facilities -> %s (ODbL schema)", table)

    return c.register(layer, assets={
        "data": {
            "href": layer.extra["hdx_geojson"],
            "type": "application/geo+json",
            "roles": ["data"],
            "title": layer.title,
            "geoportal:postgis_table": table,
        },
    }, extra_properties={"geoportal:share_alike": "ODbL-1.0"})
