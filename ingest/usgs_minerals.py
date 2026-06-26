"""USGS Africa mineral resources (public domain) — Cameroon subset into PostGIS.

Downloads the USGS Africa GIS File GeoDatabase, finds the mineral/geology
feature classes (facilities, occurrences, deposits, coal), clips each to
Cameroon, and loads them. US Geological Survey work = public domain.
"""
from __future__ import annotations

import re
import zipfile

import _common as c
from catalog.collections import Layer


def _sanitize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    zip_path = c.WORK_DIR / "usgs_africa_gis.gdb.zip"
    c.download(layer.extra["gdb_zip"], zip_path)
    extract_dir = c.WORK_DIR / "usgs_africa_gis"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    gdb = next(p for p in extract_dir.rglob("*.gdb") if p.is_dir())

    import fiona

    all_layers = fiona.listlayers(str(gdb))
    c.log.info("USGS GDB feature classes: %d", len(all_layers))
    match = layer.extra["layer_match"]
    wanted = [gl for gl in all_layers if any(m in gl.lower() for m in match)]
    c.log.info("matched mineral/geology layers: %s", wanted)

    assets: dict[str, dict] = {}
    for gl in wanted:
        table = f"usgs_{_sanitize(gl)}"[:60]
        try:
            loaded = c.load_vector_to_postgis(
                gdb, schema="layers", table=table, src_layer=gl, promote_multi=True,
            )
        except Exception as exc:  # some FCs may be empty over Cameroon
            c.log.info("skip %s (%s)", gl, exc)
            continue
        assets[_sanitize(gl)] = {
            "href": layer.extra["gdb_zip"],
            "type": "application/x-filegdb",
            "roles": ["data"],
            "title": gl,
            "geoportal:postgis_table": loaded,
        }
        c.log.info("loaded %s -> %s", gl, loaded)

    if not assets:
        raise RuntimeError("No USGS mineral layers loaded for Cameroon")
    return c.register(layer, assets=assets)
