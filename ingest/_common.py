"""Shared ingestion helpers — download, clip, COG, PostGIS, register.

Designed to run **inside the worker container** (`docker compose run --rm
worker ...`), which ships the GDAL CLI (`gdalwarp`, `gdal_translate`,
`ogr2ogr`) plus the Python geo stack. The host does not need GDAL.

Every per-dataset script calls, in order:

    ensure_license_cleared(layer)   # the policy gate
    ... download / clip / standardize ...
    register(layer, assets=...)     # validated STAC item -> pgSTAC

so the four-step contract in ``ingest/README.md`` is enforced in one place.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

# --- make the `catalog` package importable ---------------------------------
# In the container the repo's `catalog/` is mounted at /app/catalog (see
# docker-compose). For local dev, walk up to the repo root. We add the *parent*
# of catalog/ to sys.path and import `catalog.*` (dotted) so our collections.py
# never shadows the stdlib `collections` module.
for _candidate in ("/app", str(Path(__file__).resolve().parents[1])):
    if (Path(_candidate) / "catalog" / "__init__.py").exists():
        if _candidate not in sys.path:
            sys.path.insert(0, _candidate)
        break

from catalog.collections import CAMEROON_BBOX, Layer  # noqa: E402
from catalog.register import build_item, load_items, write_item  # noqa: E402

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [ingest] %(message)s",
)
log = logging.getLogger("ingest")

# Work + output directories live in the `exports` named volume so results
# survive between `docker compose run` invocations.
WORK_DIR = Path(os.environ.get("GEOPORTAL_WORK_DIR", "/exports/_ingest_work"))
COG_DIR = Path(os.environ.get("GEOPORTAL_COG_DIR", "/exports/cogs"))
PGSTAC_DSN = os.environ.get("PGSTAC_DSN") or os.environ.get("DATABASE_URL", "")


# ---------------------------------------------------------------------------
# Policy gate
# ---------------------------------------------------------------------------
def ensure_license_cleared(layer: Layer) -> None:
    """Abort ingestion unless the layer's license was confirmed + recorded.

    The flag mirrors the verification log in ``data-licenses.md``; it is the
    code-level expression of "fetch and confirm the license before download".
    """
    if not layer.license_confirmed:
        raise PermissionError(
            f"License for {layer.id!r} is not confirmed — refusing to ingest. "
            f"Verify {layer.source_url} and record it in data-licenses.md first."
        )
    log.info(
        "license OK: %s -> %s (checked %s)",
        layer.id, layer.license, layer.license_checked,
    )


# ---------------------------------------------------------------------------
# Small process + IO helpers
# ---------------------------------------------------------------------------
def run(cmd: list[str]) -> None:
    """Run a subprocess, streaming output; raise on non-zero exit."""
    log.info("$ %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def ensure_dirs() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    COG_DIR.mkdir(parents=True, exist_ok=True)


def download(url: str, dest: Path, *, auth: tuple[str, str] | None = None) -> Path:
    """Stream ``url`` to ``dest`` (skips if already present and non-empty)."""
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log.info("cached: %s", dest)
        return dest
    log.info("download: %s -> %s", url, dest)
    with requests.get(url, stream=True, auth=auth, timeout=600) as resp:
        resp.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
        tmp.replace(dest)
    return dest


# ---------------------------------------------------------------------------
# Raster: clip to Cameroon + convert to COG
# ---------------------------------------------------------------------------
def cameroon_cutline() -> Path:
    """Return a GeoJSON of Cameroon's ADM0 boundary, used as a raster cutline.

    Sourced from geoBoundaries (CC-BY 4.0) so the clip mask itself is an open
    layer. Cached in the work dir.
    """
    out = WORK_DIR / "cmr_adm0.geojson"
    if out.exists() and out.stat().st_size > 0:
        return out
    # geoBoundaries open API: simplified ADM0 GeoJSON for Cameroon.
    meta_url = "https://www.geoboundaries.org/api/current/gbOpen/CMR/ADM0/"
    import requests

    meta = requests.get(meta_url, timeout=120).json()
    gj_url = meta["simplifiedGeometryGeoJSON"]
    download(gj_url, out)
    return out


def clip_raster_to_cameroon(src: Path, dst: Path, *, nodata: float | None = None) -> Path:
    """Clip ``src`` raster to the Cameroon cutline with gdalwarp."""
    cutline = cameroon_cutline()
    cmd = [
        "gdalwarp", "-overwrite",
        "-cutline", str(cutline), "-crop_to_cutline",
        "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE",
    ]
    if nodata is not None:
        cmd += ["-dstnodata", str(nodata)]
    cmd += [str(src), str(dst)]
    run(cmd)
    return dst


def to_cog(src: Path, dst: Path, *, web_optimized: bool = True) -> Path:
    """Convert a GeoTIFF to a Cloud-Optimized GeoTIFF via rio-cogeo."""
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles

    dst.parent.mkdir(parents=True, exist_ok=True)
    profile = cog_profiles.get("deflate")
    log.info("cog: %s -> %s", src, dst)
    cog_translate(
        str(src), str(dst), profile,
        web_optimized=web_optimized, forward_band_tags=True, quiet=False,
    )
    return dst


# ---------------------------------------------------------------------------
# Vector: clip + load to PostGIS
# ---------------------------------------------------------------------------
def load_vector_to_postgis(
    src: Path, *, schema: str, table: str, src_layer: str | None = None,
    where: str | None = None, promote_multi: bool = True,
) -> str:
    """Clip ``src`` to the Cameroon bbox and load it into PostGIS via ogr2ogr.

    Returns the fully-qualified ``schema.table`` name. ODbL layers must pass the
    ``osm_odbl`` schema so they stay isolated (see init SQL + data-licenses.md).
    """
    if not PGSTAC_DSN:
        raise RuntimeError("PGSTAC_DSN/DATABASE_URL not set — cannot load to PostGIS")
    min_x, min_y, max_x, max_y = CAMEROON_BBOX
    cmd = [
        "ogr2ogr", "-f", "PostgreSQL",
        f"PG:{PGSTAC_DSN}", str(src),
        "-nln", f"{schema}.{table}",
        "-lco", f"SCHEMA={schema}",
        "-lco", "GEOMETRY_NAME=geom",
        "-t_srs", "EPSG:4326",
        "-spat", str(min_x), str(min_y), str(max_x), str(max_y),
        "-overwrite", "-progress",
    ]
    if promote_multi:
        cmd += ["-nlt", "PROMOTE_TO_MULTI"]
    if where:
        cmd += ["-where", where]
    if src_layer:
        cmd.append(src_layer)
    run(cmd)
    return f"{schema}.{table}"


# ---------------------------------------------------------------------------
# Optional object storage (Cloudflare R2 / S3-compatible)
# ---------------------------------------------------------------------------
def upload_cog(local: Path, key: str) -> str:
    """Upload a COG to R2 if configured; otherwise return its local href.

    Returns the asset href to record in the STAC item.
    """
    endpoint = os.environ.get("R2_ENDPOINT_URL", "")
    bucket = os.environ.get("R2_BUCKET", "")
    public_base = os.environ.get("R2_PUBLIC_BASE_URL", "")
    access = os.environ.get("R2_ACCESS_KEY_ID", "")
    if not (endpoint and bucket and access and "REPLACE_ME" not in access):
        log.warning("R2 not configured — keeping COG local at %s", local)
        return local.as_uri()

    import boto3

    s3 = boto3.client(
        "s3", endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )
    s3.upload_file(str(local), bucket, key, ExtraArgs={"ContentType": "image/tiff"})
    href = f"{public_base.rstrip('/')}/{key}" if public_base else f"{endpoint}/{bucket}/{key}"
    log.info("uploaded: %s", href)
    return href


# ---------------------------------------------------------------------------
# Register a validated STAC item
# ---------------------------------------------------------------------------
def register(layer: Layer, *, assets: dict, bbox: list[float] | None = None,
             extra_properties: dict | None = None) -> dict:
    """Build a validated STAC item and load it into pgSTAC (or write JSON).

    If no database DSN is configured, the validated item is written to
    ``WORK_DIR/<id>.json`` so the pipeline is still exercised end-to-end.
    """
    item = build_item(layer, assets=assets, bbox=bbox, extra_properties=extra_properties)
    if PGSTAC_DSN:
        try:
            load_items([item], PGSTAC_DSN)
            log.info("registered in pgSTAC: %s", layer.id)
            return item
        except Exception as exc:  # pgstac not migrated yet, etc.
            log.warning("pgSTAC load failed (%s) — writing JSON instead", exc)
    out = WORK_DIR / f"{layer.id}.json"
    write_item(item, str(out))
    log.info("wrote STAC item: %s", out)
    return item
