"""Administrative boundaries — UN OCHA COD-AB into PostGIS, perfectly nested.

Replaces the geoBoundaries gbOpen levels, whose ADM0–ADM3 were sourced
independently and did not nest (misaligned shared borders / slivers).

The fieldmaps.io edge-matched COD ships a single ADM3 layer that already carries
the full PCODE hierarchy (adm0_id … adm3_id). We load ADM3, then build ADM2/1/0
by dissolving ADM3 on each parent id — so every higher level is *exactly* the
union of its children and the shared borders align by construction.

Source: OCHA / Institut National de Cartographie (INC), Cameroon. CC-BY-IGO 3.0.
"""
from __future__ import annotations

import zipfile

import _common as c
from catalog.collections import Layer

# level -> the grouping columns that define it (dissolve ADM3 up to this level).
# COD-AB carries PCODEs (unique ids) + EN/FR names at every level.
_DISSOLVE = {
    "adm2": ["adm2_pcode", "adm2_en", "adm2_fr", "adm1_pcode", "adm1_en", "adm1_fr",
             "adm0_pcode", "adm0_en", "adm0_fr"],
    "adm1": ["adm1_pcode", "adm1_en", "adm1_fr", "adm0_pcode", "adm0_en", "adm0_fr"],
    "adm0": ["adm0_pcode", "adm0_en", "adm0_fr"],
}


def ingest(layer: Layer) -> dict:
    c.ensure_license_cleared(layer)
    c.ensure_dirs()

    # Filename keys off the source so a source change busts the cache.
    zip_path = c.WORK_DIR / "cmr_cod_originals.gpkg.zip"
    c.download(layer.extra["gpkg_zip"], zip_path)
    extract_dir = c.WORK_DIR / "cmr_cod_originals"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    gpkg = next(extract_dir.rglob("*.gpkg"))

    import fiona

    gpkg_layers = fiona.listlayers(str(gpkg))
    c.log.info("COD gpkg layers: %s", gpkg_layers)
    adm3_layer = next((gl for gl in gpkg_layers if gl.lower().endswith("adm3")), gpkg_layers[0])

    # 1. Load the finest level.
    c.load_vector_to_postgis(gpkg, schema="layers", table="admin_adm3", src_layer=adm3_layer)

    # 2. Defensive clean: clip any spurious spike vertices to a padded Cameroon
    #    envelope (some COD builds carry junk vertices at e.g. lon 27.6 / lat -9.8).
    _clean_adm3()

    # 3. Dissolve ADM3 -> ADM2 -> ADM1 -> ADM0 (guarantees nesting).
    _dissolve_levels()

    levels = ["adm0", "adm1", "adm2", "adm3"]
    assets = {
        lvl: {
            "href": layer.extra["gpkg_zip"],
            "type": "application/geopackage+sqlite3",
            "roles": ["data"],
            "title": f"Administrative boundaries {lvl.upper()} (OCHA COD-AB)",
            "geoportal:postgis_table": f"layers.admin_{lvl}",
        }
        for lvl in levels
    }

    _cleanup_old()

    return c.register(layer, assets=assets, extra_properties={
        "geoportal:admin_levels": [lvl.upper() for lvl in levels],
        "geoportal:nested": True,
    })


def _clean_adm3() -> None:
    """Clip ADM3 geometries to a padded Cameroon envelope, dropping spike vertices.

    Cameroon's true extent is ~8.40–16.21 E, 1.65–13.10 N; the padded envelope
    (8.2–16.4 E, 1.4–13.3 N) is outside all real data, so this removes only junk
    spikes while leaving every real boundary untouched.
    """
    import psycopg

    with psycopg.connect(c.PGSTAC_DSN, autocommit=True) as conn:
        conn.execute(
            "UPDATE layers.admin_adm3 SET geom = "
            "  ST_Multi(ST_CollectionExtract(ST_MakeValid("
            "    ST_Intersection(geom, ST_MakeEnvelope(8.2, 1.4, 16.4, 13.3, 4326))"
            "  ), 3))::geometry(MultiPolygon, 4326)"
        )
        n = conn.execute(
            "SELECT count(*) FROM layers.admin_adm3 WHERE ST_XMax(geom) > 16.5 "
            "OR ST_XMin(geom) < 8.1 OR ST_YMax(geom) > 13.4 OR ST_YMin(geom) < 1.3"
        ).fetchone()[0]
        c.log.info("cleaned ADM3 spikes; out-of-envelope features remaining: %s", n)


def _dissolve_levels() -> None:
    import psycopg

    with psycopg.connect(c.PGSTAC_DSN, autocommit=True) as conn:
        for level, cols in _DISSOLVE.items():
            col_list = ", ".join(cols)
            conn.execute(f"DROP TABLE IF EXISTS layers.admin_{level} CASCADE")
            conn.execute(
                f"CREATE TABLE layers.admin_{level} AS "
                f"SELECT {col_list}, "
                f"  ST_Multi(ST_Union(geom))::geometry(MultiPolygon,4326) AS geom "
                f"FROM layers.admin_adm3 GROUP BY {col_list}"
            )
            conn.execute(f"CREATE INDEX ON layers.admin_{level} USING GIST (geom)")
            c.log.info("dissolved ADM3 -> layers.admin_%s", level)


def _cleanup_old() -> None:
    """Drop the superseded gbOpen tables + stale STAC item (best-effort)."""
    if not c.PGSTAC_DSN:
        return
    try:
        import psycopg

        # search_path=pgstac so the items partition trigger resolves its tables.
        with psycopg.connect(
            c.PGSTAC_DSN, autocommit=True, options="-c search_path=pgstac,public"
        ) as conn:
            for n in range(4):
                conn.execute(f"DROP TABLE IF EXISTS layers.geoboundaries_adm{n} CASCADE")
            conn.execute("DELETE FROM pgstac.items WHERE id = %s", ("geoboundaries-adm",))
        c.log.info("dropped old geoboundaries_adm0..3 + stale STAC item")
    except Exception as exc:
        c.log.warning("cleanup of old geoboundaries failed: %s", exc)
