"""Natural Earth vectors (public domain) — places, rivers, lakes.

Natural Earth is global 1:10m data in the public domain. Each layer is
downloaded as a shapefile zip, clipped to Cameroon, and loaded to PostGIS.
"""
from __future__ import annotations

import zipfile

import _common as c
from catalog.collections import Layer


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    zip_path = c.WORK_DIR / f"{layer.extra['ne_shp']}.zip"
    c.download(layer.extra["ne_zip"], zip_path)
    out_dir = c.WORK_DIR / layer.extra["ne_shp"]
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    shp = next(out_dir.rglob(f"{layer.extra['ne_shp']}.shp"))

    table = c.load_vector_to_postgis(
        shp, schema="layers", table=layer.extra["table"], src_layer=layer.extra["ne_shp"],
    )
    c.log.info("loaded Natural Earth -> %s", table)

    return c.register(layer, assets={
        "data": {
            "href": layer.extra["ne_zip"],
            "type": "application/zip",
            "roles": ["data"],
            "title": layer.title,
            "geoportal:postgis_table": table,
        },
    })
