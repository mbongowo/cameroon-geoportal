"""Thin pgSTAC access layer.

Reads the catalog through pgSTAC's own SQL functions so items come back
fully *hydrated* (merged with their collection's base item). psycopg adapts
``jsonb`` to Python dict/list automatically, so callers get plain data.

A single-connection pool is opened lazily and reused across requests.
"""
from __future__ import annotations

import json
from typing import Any

import psycopg
from psycopg_pool import ConnectionPool

from app.config import settings

_pool: ConnectionPool | None = None

# pgSTAC functions reference their tables (e.g. ``searches``) unqualified, so
# every connection needs ``pgstac`` on the search_path. Set it via the libpq
# startup options (no transaction — a configure callback that ran SET would
# leave the connection INTRANS and be rejected by the pool).
_CONN_KWARGS = {"options": "-c search_path=pgstac,public"}


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.pgstac_dsn, min_size=1, max_size=4, open=True,
            kwargs=_CONN_KWARGS,
        )
    return _pool


def _scalar(sql: str, params: tuple[Any, ...] = ()) -> Any:
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row else None


def search(body: dict[str, Any]) -> dict[str, Any]:
    """Run a pgSTAC search; returns a hydrated GeoJSON FeatureCollection."""
    result = _scalar("SELECT pgstac.search(%s::jsonb)", (json.dumps(body),))
    return result or {"type": "FeatureCollection", "features": []}


def all_collections() -> list[dict[str, Any]]:
    """Return all collections (hydrated) from pgSTAC."""
    return _scalar("SELECT pgstac.all_collections()") or []


def get_item(item_id: str) -> dict[str, Any] | None:
    """Return a single hydrated item by id, or None."""
    fc = search({"ids": [item_id], "limit": 1})
    features = fc.get("features") or []
    return features[0] if features else None
