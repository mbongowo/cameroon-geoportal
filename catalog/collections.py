"""STAC collection + layer definitions — the single source of truth for the MVP.

Two collections enforce the licensing policy structurally:

- ``cameroon-open`` — Public Domain / Copernicus-open / CC-BY 4.0 layers.
- ``osm-odbl``      — OpenStreetMap (ODbL share-alike), kept **isolated** so the
  share-alike obligation can never contaminate the open products.

Every layer carries its ``license`` and ready-to-copy ``attribution`` here, and
both fields are re-validated at registration time (see ``register.py``).
Licenses were confirmed by live fetch on 2026-06-24 — see ``../data-licenses.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Cameroon national bounding box (WGS84) — [min_lon, min_lat, max_lon, max_lat].
# Used as the default spatial extent and as a coarse pre-clip envelope.
CAMEROON_BBOX: list[float] = [8.40, 1.65, 16.21, 13.10]

# Allowed license identifiers. Anything else is rejected at registration.
ALLOWED_LICENSES: set[str] = {
    "public-domain",
    "copernicus-free-open",
    "CC-BY-4.0",
    "ODbL-1.0",
}

COLLECTION_OPEN = "cameroon-open"
COLLECTION_OSM = "osm-odbl"


@dataclass(frozen=True)
class Layer:
    """One MVP dataset and everything needed to ingest + attribute it."""

    id: str
    title: str
    theme: str
    datatype: str  # "raster" | "vector"
    license: str
    attribution: str
    collection: str
    source_url: str
    # ``True`` only once the license page has been fetched + recorded in the log.
    license_confirmed: bool = False
    license_checked: str = ""  # ISO date of the live verification
    # Free-form per-dataset hints consumed by the ingest scripts.
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# The six MVP layers. ``license_confirmed`` mirrors data-licenses.md exactly;
# the ingest gate refuses to download anything where this is False.
# ---------------------------------------------------------------------------
LAYERS: list[Layer] = [
    Layer(
        id="srtm-30m-dem",
        title="SRTM 30 m DEM",
        theme="elevation",
        datatype="raster",
        license="public-domain",
        attribution="Elevation data: NASA SRTM (public domain).",
        collection=COLLECTION_OPEN,
        source_url="https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl1-003",
        license_confirmed=True,
        license_checked="2026-06-24",
        extra={"earthaccess_short_name": "SRTMGL1", "earthaccess_version": "003"},
    ),
    Layer(
        id="sentinel2-mosaic",
        title="Sentinel-2 cloud-free mosaic",
        theme="imagery",
        datatype="raster",
        license="copernicus-free-open",
        attribution=(
            "Contains modified Copernicus Sentinel-2 data, processed for the "
            "Cameroon Geoportal."
        ),
        collection=COLLECTION_OPEN,
        source_url="https://dataspace.copernicus.eu/terms-and-conditions",
        license_confirmed=True,
        license_checked="2026-06-24",
        extra={"stac_collection": "sentinel-2-l2a", "max_cloud_cover": 10},
    ),
    Layer(
        id="esa-worldcover-10m",
        title="ESA WorldCover 10 m",
        theme="landcover",
        datatype="raster",
        license="CC-BY-4.0",
        attribution=(
            "© ESA WorldCover project 2021 / Contains modified Copernicus "
            "Sentinel data (2021) processed by ESA WorldCover consortium, "
            "licensed under CC-BY 4.0."
        ),
        collection=COLLECTION_OPEN,
        source_url="https://esa-worldcover.org/en/data-access",
        license_confirmed=True,
        license_checked="2026-06-24",
        extra={"version": "v200", "year": 2021},
    ),
    Layer(
        id="geoboundaries-adm",
        title="geoBoundaries ADM0–ADM3",
        theme="boundaries",
        datatype="vector",
        license="CC-BY-4.0",
        attribution=(
            "Administrative boundaries: geoBoundaries (www.geoboundaries.org), "
            "CC-BY 4.0."
        ),
        collection=COLLECTION_OPEN,
        source_url="https://www.geoboundaries.org",
        license_confirmed=True,
        license_checked="2026-06-24",
        extra={"iso3": "CMR", "levels": ["ADM0", "ADM1", "ADM2", "ADM3"]},
    ),
    Layer(
        id="worldpop-population",
        title="WorldPop population",
        theme="population",
        datatype="raster",
        license="CC-BY-4.0",
        attribution=(
            "Population data: WorldPop (www.worldpop.org), University of "
            "Southampton, CC-BY 4.0."
        ),
        collection=COLLECTION_OPEN,
        source_url="https://hub.worldpop.org/data/licence.txt",
        license_confirmed=True,
        license_checked="2026-06-24",
        extra={"iso3": "CMR", "year": 2020, "product": "ppp_constrained"},
    ),
    Layer(
        id="osm-roads",
        title="OpenStreetMap roads",
        theme="transport",
        datatype="vector",
        license="ODbL-1.0",
        attribution="© OpenStreetMap contributors, ODbL (www.openstreetmap.org/copyright).",
        collection=COLLECTION_OSM,  # isolated tier
        source_url="https://www.openstreetmap.org/copyright",
        license_confirmed=True,
        license_checked="2026-06-24",
        extra={"geofabrik_pbf": "https://download.geofabrik.de/africa/cameroon-latest.osm.pbf"},
    ),
]

LAYERS_BY_ID: dict[str, Layer] = {layer.id: layer for layer in LAYERS}

# Map the ``--layer <name>`` CLI alias to the canonical layer id.
LAYER_ALIASES: dict[str, str] = {
    "srtm": "srtm-30m-dem",
    "sentinel2": "sentinel2-mosaic",
    "worldcover": "esa-worldcover-10m",
    "geoboundaries": "geoboundaries-adm",
    "worldpop": "worldpop-population",
    "osm_roads": "osm-roads",
    "osm": "osm-roads",
}


def resolve_layer(name: str) -> Layer:
    """Resolve a CLI alias or canonical id to a :class:`Layer`."""
    layer_id = LAYER_ALIASES.get(name, name)
    if layer_id not in LAYERS_BY_ID:
        valid = ", ".join(sorted(LAYER_ALIASES) | set(LAYERS_BY_ID))
        raise KeyError(f"Unknown layer {name!r}. Valid: {valid}")
    return LAYERS_BY_ID[layer_id]


# ---------------------------------------------------------------------------
# STAC Collection bodies (license metadata travels with the collection too).
# ---------------------------------------------------------------------------
def collection_dicts() -> dict[str, dict]:
    """Return STAC Collection JSON for both tiers, keyed by collection id."""
    spatial = {"bbox": [CAMEROON_BBOX]}
    temporal = {"interval": [["2000-01-01T00:00:00Z", None]]}
    return {
        COLLECTION_OPEN: {
            "type": "Collection",
            "stac_version": "1.0.0",
            "id": COLLECTION_OPEN,
            "title": "Cameroon — open layers",
            "description": (
                "Public-domain, Copernicus-open and CC-BY 4.0 layers clipped to "
                "Cameroon. Redistributable for a cost-recovery fee with attribution."
            ),
            "license": "various-open",  # per-item license is authoritative
            "extent": {"spatial": spatial, "temporal": temporal},
            "providers": [
                {"name": "Cameroon Geoportal", "roles": ["processor", "host"]},
            ],
            "links": [],
        },
        COLLECTION_OSM: {
            "type": "Collection",
            "stac_version": "1.0.0",
            "id": COLLECTION_OSM,
            "title": "Cameroon — OpenStreetMap (ODbL)",
            "description": (
                "OpenStreetMap-derived layers. ODbL 1.0 share-alike — kept "
                "isolated from the open tier so share-alike never contaminates "
                "other products."
            ),
            "license": "ODbL-1.0",
            "extent": {"spatial": spatial, "temporal": temporal},
            "providers": [
                {"name": "OpenStreetMap contributors", "roles": ["producer", "licensor"]},
                {"name": "Cameroon Geoportal", "roles": ["processor", "host"]},
            ],
            "links": [],
        },
    }
