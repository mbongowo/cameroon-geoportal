"""Build, validate, and load STAC items — with the license gate enforced.

The hard rule of the project: **no item without a `license` and an
`attribution` may enter the catalog.** ``validate_item`` enforces it and is
called by ``build_item`` before any item is returned, so it is impossible to
construct a non-compliant item through this module.

``load_items`` upserts validated items into pgSTAC. pgSTAC / pypgstac are
imported lazily so this module stays importable (and unit-testable) without a
database or the pgstac package present.
"""
from __future__ import annotations

import datetime as _dt
import json
from typing import Any, Iterable

# Always import the layer module via the ``catalog`` package (dotted), never as a
# bare ``import collections`` — that would shadow the standard library.
from .collections import (
    ALLOWED_LICENSES,
    CAMEROON_BBOX,
    Layer,
    collection_dicts,
)


class LicenseError(ValueError):
    """Raised when an item violates the license/attribution policy."""


def validate_item(item: dict[str, Any]) -> None:
    """Reject any STAC item missing a valid license or attribution.

    Raises :class:`LicenseError` describing the first violation found.
    """
    item_id = item.get("id", "<no-id>")
    props = item.get("properties", {})

    license_id = item.get("license") or props.get("license")
    if not license_id:
        raise LicenseError(f"item {item_id!r}: missing 'license'")
    if license_id not in ALLOWED_LICENSES:
        raise LicenseError(
            f"item {item_id!r}: license {license_id!r} not in allowed set "
            f"{sorted(ALLOWED_LICENSES)}"
        )

    attribution = props.get("attribution")
    if not attribution or not str(attribution).strip():
        raise LicenseError(f"item {item_id!r}: missing 'properties.attribution'")


def _bbox_to_polygon(bbox: list[float]) -> dict[str, Any]:
    min_x, min_y, max_x, max_y = bbox
    return {
        "type": "Polygon",
        "coordinates": [[
            [min_x, min_y], [max_x, min_y], [max_x, max_y],
            [min_x, max_y], [min_x, min_y],
        ]],
    }


def build_item(
    layer: Layer,
    *,
    assets: dict[str, dict[str, Any]],
    bbox: list[float] | None = None,
    geometry: dict[str, Any] | None = None,
    datetime: _dt.datetime | None = None,
    extra_properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a validated STAC Item dict for ``layer``.

    ``license`` and ``properties.attribution`` are taken from the layer
    definition (the audited source of truth) and the result is validated before
    it is returned — a non-compliant item cannot be produced.
    """
    bbox = bbox or CAMEROON_BBOX
    geometry = geometry or _bbox_to_polygon(bbox)
    when = datetime or _dt.datetime(2021, 1, 1, tzinfo=_dt.timezone.utc)

    properties: dict[str, Any] = {
        "datetime": when.isoformat(),
        "attribution": layer.attribution,
        "license": layer.license,
        "title": layer.title,
        "theme": layer.theme,
        "geoportal:datatype": layer.datatype,
        "geoportal:source_url": layer.source_url,
        "geoportal:license_checked": layer.license_checked,
    }
    if extra_properties:
        properties.update(extra_properties)

    item = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": layer.id,
        "collection": layer.collection,
        "license": layer.license,
        "bbox": bbox,
        "geometry": geometry,
        "properties": properties,
        "assets": assets,
        "links": [],
    }
    validate_item(item)
    return item


def load_items(items: Iterable[dict[str, Any]], dsn: str) -> int:
    """Upsert validated items (and their collections) into pgSTAC.

    Returns the number of items loaded. Imports pypgstac lazily.
    """
    items = list(items)
    for item in items:
        validate_item(item)

    from pypgstac.db import PgstacDB  # type: ignore[import-not-found]
    from pypgstac.load import Loader, Methods  # type: ignore[import-not-found]

    collections = list(collection_dicts().values())
    with PgstacDB(dsn=dsn) as db:
        loader = Loader(db=db)
        loader.load_collections(iter(collections), insert_mode=Methods.upsert)
        loader.load_items(iter(items), insert_mode=Methods.upsert)
    return len(items)


def write_item(item: dict[str, Any], path: str) -> None:
    """Validate and write a single item to ``path`` as pretty JSON (debug aid)."""
    validate_item(item)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(item, fh, indent=2)
