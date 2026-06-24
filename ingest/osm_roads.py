"""OpenStreetMap roads (ODbL 1.0) — Geofabrik Cameroon extract into PostGIS.

ODbL is share-alike, so this layer is loaded into the **isolated** ``osm_odbl``
schema and registered in the **separate** ``osm-odbl`` STAC collection. It is
never merged with the open layers.
"""
from __future__ import annotations

import _common as c
from catalog.collections import Layer

# OSM "lines" layer carries the road network; keep only highway-tagged features.
ROADS_WHERE = "highway IS NOT NULL"


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    pbf_url = layer.extra["geofabrik_pbf"]
    pbf = c.WORK_DIR / "cameroon-latest.osm.pbf"
    c.download(pbf_url, pbf)

    # ogr2ogr reads the OSM PBF "lines" layer directly (GDAL OSM driver).
    table = c.load_vector_to_postgis(
        pbf, schema="osm_odbl", table="roads",
        src_layer="lines", where=ROADS_WHERE, promote_multi=True,
    )
    c.log.info("loaded OSM roads -> %s (isolated ODbL schema)", table)

    return c.register(layer, assets={
        "data": {
            "href": pbf_url,
            "type": "application/x-protobuf; format=osm-pbf",
            "roles": ["data"],
            "title": "OpenStreetMap roads (Geofabrik Cameroon extract)",
            "geoportal:postgis_table": table,
        },
    }, extra_properties={"geoportal:share_alike": "ODbL-1.0"})
