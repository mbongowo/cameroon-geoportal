#!/usr/bin/env python3
"""Install / upgrade the pgSTAC schema and load the two collections.

Run once before ingestion (inside the worker container, which has DB access):

    docker compose run --rm worker python /app/catalog/migrate.py

pgSTAC is installed via ``pypgstac migrate`` so its version is pinned and
reproducible (the init SQL deliberately leaves the catalog schema to this step).
"""
from __future__ import annotations

import os
import sys

# Allow running as a script: ensure the `catalog` package is importable.
sys.path.insert(0, "/app")

from catalog.collections import collection_dicts  # noqa: E402


def main() -> int:
    dsn = os.environ.get("PGSTAC_DSN") or os.environ.get("DATABASE_URL")
    if not dsn:
        print("PGSTAC_DSN/DATABASE_URL not set", file=sys.stderr)
        return 2

    from pypgstac.db import PgstacDB
    from pypgstac.load import Loader, Methods
    from pypgstac.migrate import Migrate

    with PgstacDB(dsn=dsn) as db:
        version = Migrate(db).run_migration()
        print(f"pgSTAC migrated to version {version}")
        loader = Loader(db=db)
        loader.load_collections(
            iter(list(collection_dicts().values())), insert_mode=Methods.upsert,
        )
        print("loaded collections: cameroon-open, osm-odbl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
