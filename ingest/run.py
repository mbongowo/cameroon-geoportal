#!/usr/bin/env python3
"""Ingestion dispatcher.

    python /ingest/run.py --layer srtm
    python /ingest/run.py --all
    python /ingest/run.py --list

Each layer's license is re-checked at the top of its ``ingest()`` (the policy
gate) before anything is downloaded.
"""
from __future__ import annotations

import argparse
import importlib
import sys

import _common as c
from catalog.collections import LAYER_ALIASES, LAYERS, resolve_layer

# Map canonical layer id -> the module that ingests it.
MODULES: dict[str, str] = {
    "srtm-30m-dem": "srtm",
    "sentinel2-mosaic": "sentinel2",
    "esa-worldcover-10m": "worldcover",
    "admin-boundaries": "admin_boundaries",
    "worldpop-population": "worldpop",
    "osm-roads": "osm_roads",
}

# Sensible order: boundaries first (they provide the clip cutline), then rasters.
DEFAULT_ORDER = [
    "admin-boundaries", "srtm-30m-dem", "esa-worldcover-10m",
    "worldpop-population", "sentinel2-mosaic", "osm-roads",
]


def ingest_one(name: str) -> None:
    layer = resolve_layer(name)
    module = importlib.import_module(MODULES[layer.id])
    c.log.info("=== ingest %s (%s) ===", layer.id, layer.license)
    module.ingest(layer)
    c.log.info("=== done %s ===", layer.id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cameroon Geoportal ingestion")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--layer", help="layer alias or id (see --list)")
    group.add_argument("--all", action="store_true", help="ingest every MVP layer")
    group.add_argument("--list", action="store_true", help="list layers and exit")
    args = parser.parse_args(argv)

    if args.list:
        for layer in LAYERS:
            ok = "OK" if layer.license_confirmed else "PENDING"
            print(f"{layer.id:24s} {layer.license:22s} license:{ok}")
        print("\naliases:", ", ".join(sorted(LAYER_ALIASES)))
        return 0

    targets = DEFAULT_ORDER if args.all else [args.layer]
    failures = []
    for name in targets:
        try:
            ingest_one(name)
        except Exception as exc:  # keep going; report at the end
            c.log.error("FAILED %s: %s", name, exc)
            failures.append((name, str(exc)))

    if failures:
        c.log.error("%d layer(s) failed:", len(failures))
        for name, err in failures:
            c.log.error("  - %s: %s", name, err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
