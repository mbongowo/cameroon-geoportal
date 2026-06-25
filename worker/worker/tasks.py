"""Celery tasks.

`clip_export` is the portal's headline job: clip a catalog layer to a user's
area of interest, convert to the requested format, and bundle the result with
LICENSE.txt + ATTRIBUTION.txt so attribution flows all the way to the download.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

from worker.celery_app import celery_app
from worker.licenses import license_text

PGSTAC_DSN = os.environ.get("PGSTAC_DSN") or os.environ.get("DATABASE_URL", "")
BUNDLE_DIR = Path(os.environ.get("GEOPORTAL_BUNDLE_DIR", "/exports/bundles"))
WORK_DIR = Path(os.environ.get("GEOPORTAL_WORK_DIR", "/exports/_ingest_work"))


@celery_app.task(name="worker.ping")
def ping() -> str:
    """Liveness probe for the worker."""
    return "pong"


# ---------------------------------------------------------------------------
# Catalog lookup (pgSTAC)
# ---------------------------------------------------------------------------
def _get_item(item_id: str) -> dict:
    import psycopg

    with psycopg.connect(PGSTAC_DSN, options="-c search_path=pgstac,public") as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pgstac.search(%s::jsonb)",
                (json.dumps({"ids": [item_id], "limit": 1}),),
            )
            row = cur.fetchone()
    fc = (row[0] if row else None) or {}
    features = fc.get("features") or []
    if not features:
        raise ValueError(f"layer {item_id!r} not found in catalog")
    return features[0]


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _write_aoi(aoi_geometry: dict, dest: Path) -> Path:
    """Write the AOI geometry as a GeoJSON FeatureCollection for use as a cutline."""
    fc = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}, "geometry": aoi_geometry}],
    }
    dest.write_text(json.dumps(fc), encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# Per-type clip
# ---------------------------------------------------------------------------
def _clip_raster(item: dict, aoi: Path, out_dir: Path) -> list[Path]:
    href = item["assets"].get("data", {}).get("href", "")
    src = href.replace("file://", "")
    out = out_dir / f"{item['id']}.tif"
    _run([
        "gdalwarp", "-overwrite", "-of", "GTiff",
        "-cutline", str(aoi), "-crop_to_cutline",
        "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE",
        src, str(out),
    ])
    return [out]


def _clip_vector(item: dict, aoi: Path, out_dir: Path, fmt: str) -> list[Path]:
    """Clip each PostGIS table backing the item to the AOI.

    GeoPackage collects every table as one multi-layer file; GeoJSON writes one
    file per table.
    """
    tables = [
        a["geoportal:postgis_table"]
        for a in item["assets"].values()
        if a.get("geoportal:postgis_table")
    ]
    outputs: list[Path] = []
    if fmt == "geopackage":
        gpkg = out_dir / f"{item['id']}.gpkg"
        for i, table in enumerate(tables):
            layer_name = table.split(".")[-1]
            # First layer creates the file; later layers append into it.
            mode = ["-f", "GPKG"] if i == 0 else ["-update", "-append"]
            _run([
                "ogr2ogr", *mode, str(gpkg), f"PG:{PGSTAC_DSN}",
                table, "-nln", layer_name, "-clipsrc", str(aoi),
                "-nlt", "PROMOTE_TO_MULTI",
            ])
        outputs.append(gpkg)
    else:  # geojson
        for table in tables:
            layer_name = table.split(".")[-1]
            out = out_dir / f"{layer_name}.geojson"
            _run([
                "ogr2ogr", "-f", "GeoJSON", str(out), f"PG:{PGSTAC_DSN}",
                table, "-clipsrc", str(aoi), "-nlt", "PROMOTE_TO_MULTI",
            ])
            outputs.append(out)
    return outputs


# ---------------------------------------------------------------------------
# The task
# ---------------------------------------------------------------------------
@celery_app.task(name="worker.clip_export", bind=True)
def clip_export(self, layer_id: str, aoi: dict, fmt: str = "geotiff") -> dict:
    """Clip ``layer_id`` to ``aoi`` and return a downloadable, attributed bundle."""
    item = _get_item(layer_id)
    props = item.get("properties", {})
    license_id = item.get("license") or props.get("license")
    attribution = props.get("attribution")
    datatype = props.get("geoportal:datatype")
    if not license_id or not attribution:
        raise ValueError(f"layer {layer_id!r} missing license/attribution — refusing export")

    token = uuid.uuid4().hex
    staging = WORK_DIR / "exports" / token
    data_dir = staging / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    aoi_path = _write_aoi(aoi, staging / "aoi.geojson")

    if datatype == "raster":
        files = _clip_raster(item, aoi_path, data_dir)
        actual_fmt = "geotiff"
    elif datatype == "vector":
        actual_fmt = fmt if fmt in ("geojson", "geopackage") else "geojson"
        files = _clip_vector(item, aoi_path, data_dir, actual_fmt)
    else:
        raise ValueError(f"unknown datatype {datatype!r} for {layer_id!r}")

    # Mandatory licence + attribution files travel with the data.
    (staging / "LICENSE.txt").write_text(license_text(license_id), encoding="utf-8")
    (staging / "ATTRIBUTION.txt").write_text(
        attribution.strip() + "\n", encoding="utf-8",
    )
    (staging / "README.txt").write_text(
        f"Cameroon Geoportal export\n"
        f"Layer: {props.get('title', layer_id)} ({layer_id})\n"
        f"License: {license_id}\n"
        f"Format: {actual_fmt}\n"
        f"Clipped to the supplied area of interest.\n\n"
        f"The fee paid covers hosting, bandwidth and curation — never the data "
        f"rights, which remain open. See LICENSE.txt and ATTRIBUTION.txt.\n",
        encoding="utf-8",
    )

    # Zip the bundle.
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    bundle = BUNDLE_DIR / f"{token}.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in staging.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(staging))
    shutil.rmtree(staging, ignore_errors=True)

    return {
        "status": "done",
        "token": token,
        "filename": f"{layer_id}.zip",
        "download_path": f"/download/{token}",
        "layer_id": layer_id,
        "format": actual_fmt,
        "license": license_id,
        "attribution": attribution,
        "files": [f.name for f in files],
    }
