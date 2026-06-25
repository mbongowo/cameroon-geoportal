"""OSM-derived themes (ODbL) — waterways, land use — from the Geofabrik extract.

Reuses the cached Cameroon PBF (same file as roads). Each layer pulls a
different OSM geometry layer / tag filter into the isolated ``osm_odbl`` schema.
"""
from __future__ import annotations

import _common as c
from catalog.collections import Layer


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    pbf = c.WORK_DIR / "cameroon-latest.osm.pbf"
    c.download(layer.extra["geofabrik_pbf"], pbf)

    table = c.load_vector_to_postgis(
        pbf, schema="osm_odbl", table=layer.extra["table"],
        src_layer=layer.extra["osm_layer"], where=layer.extra["where"],
        promote_multi=True,
    )
    c.log.info("loaded OSM %s -> %s (ODbL schema)", layer.extra["osm_layer"], table)

    return c.register(layer, assets={
        "data": {
            "href": layer.extra["geofabrik_pbf"],
            "type": "application/x-protobuf; format=osm-pbf",
            "roles": ["data"],
            "title": layer.title,
            "geoportal:postgis_table": table,
        },
    }, extra_properties={"geoportal:share_alike": "ODbL-1.0"})
