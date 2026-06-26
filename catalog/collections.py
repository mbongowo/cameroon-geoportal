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
# All permit redistribution + commercial use with (at most) attribution — no
# NonCommercial, no ShareAlike. CC-BY-IGO-3.0 (UN/OCHA) and CC-BY-3.0 are the
# attribution-only IGO/older variants of CC-BY, functionally equivalent for our
# redistribute-for-a-fee model. copernicus-dem-eula is ESA's permissive DEM
# licence (free worldwide, commercial use OK, attribution required).
ALLOWED_LICENSES: set[str] = {
    "public-domain",
    "copernicus-free-open",
    "copernicus-dem-eula",
    "CC-BY-4.0",
    "CC-BY-3.0",
    "CC-BY-IGO-3.0",
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
        # target_res_deg: output mosaic resolution (~0.0005° ≈ 55 m). Cameroon
        # spans UTM 32N/33N so the mosaic is built with a reprojecting gdalwarp,
        # not gdalbuildvrt. Full 10 m is a Phase 3+ refinement.
        extra={
            "stac_collection": "sentinel-2-l2a",
            "max_cloud_cover": 10,
            "target_res_deg": 0.0005,
        },
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
        id="admin-boundaries",
        title="Administrative boundaries (OCHA COD-AB, ADM0–3)",
        theme="boundaries",
        datatype="vector",
        license="CC-BY-IGO-3.0",
        attribution=(
            "Administrative boundaries: OCHA / Institut National de Cartographie "
            "(INC), Cameroon — Common Operational Dataset (COD-AB), CC-BY-IGO 3.0."
        ),
        collection=COLLECTION_OPEN,
        source_url="https://data.humdata.org/dataset/cod-ab-cmr",
        license_confirmed=True,
        license_checked="2026-06-25",
        # Single hierarchical (PCODE-nested) COD source — fixes the gbOpen
        # level-misalignment. Edge-matched GeoPackage from fieldmaps.io.
        extra={
            "iso3": "CMR",
            "gpkg_zip": "https://data.fieldmaps.io/cod/originals/cmr.gpkg.zip",
            "levels": ["adm0", "adm1", "adm2", "adm3"],
        },
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
    # ---- Wave 2: physical + reference vectors (Natural Earth, public domain) ----
    Layer(
        id="ne-populated-places",
        title="Populated places (Natural Earth)",
        theme="places",
        datatype="vector",
        license="public-domain",
        attribution="Populated places: Natural Earth (naturalearthdata.com, public domain).",
        collection=COLLECTION_OPEN,
        source_url="https://www.naturalearthdata.com/about/terms-of-use/",
        license_confirmed=True,
        license_checked="2026-06-25",
        extra={
            "ne_zip": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_populated_places.zip",
            "ne_shp": "ne_10m_populated_places",
            "table": "ne_populated_places",
        },
    ),
    Layer(
        id="ne-rivers",
        title="Rivers & lake centerlines (Natural Earth)",
        theme="water",
        datatype="vector",
        license="public-domain",
        attribution="Rivers: Natural Earth (naturalearthdata.com, public domain).",
        collection=COLLECTION_OPEN,
        source_url="https://www.naturalearthdata.com/about/terms-of-use/",
        license_confirmed=True,
        license_checked="2026-06-25",
        extra={
            "ne_zip": "https://naciscdn.org/naturalearth/10m/physical/ne_10m_rivers_lake_centerlines.zip",
            "ne_shp": "ne_10m_rivers_lake_centerlines",
            "table": "ne_rivers",
        },
    ),
    Layer(
        id="ne-lakes",
        title="Lakes (Natural Earth)",
        theme="water",
        datatype="vector",
        license="public-domain",
        attribution="Lakes: Natural Earth (naturalearthdata.com, public domain).",
        collection=COLLECTION_OPEN,
        source_url="https://www.naturalearthdata.com/about/terms-of-use/",
        license_confirmed=True,
        license_checked="2026-06-25",
        extra={
            "ne_zip": "https://naciscdn.org/naturalearth/10m/physical/ne_10m_lakes.zip",
            "ne_shp": "ne_10m_lakes",
            "table": "ne_lakes",
        },
    ),
    # ---- Wave 2: OSM-derived themes (ODbL, isolated tier) ----
    Layer(
        id="osm-waterways",
        title="Waterways (OpenStreetMap)",
        theme="water",
        datatype="vector",
        license="ODbL-1.0",
        attribution="© OpenStreetMap contributors, ODbL (www.openstreetmap.org/copyright).",
        collection=COLLECTION_OSM,
        source_url="https://www.openstreetmap.org/copyright",
        license_confirmed=True,
        license_checked="2026-06-24",
        extra={
            "geofabrik_pbf": "https://download.geofabrik.de/africa/cameroon-latest.osm.pbf",
            "osm_layer": "lines",
            "where": "waterway IS NOT NULL",
            "table": "waterways",
        },
    ),
    Layer(
        id="osm-landuse",
        title="Land use (OpenStreetMap)",
        theme="landuse",
        datatype="vector",
        license="ODbL-1.0",
        attribution="© OpenStreetMap contributors, ODbL (www.openstreetmap.org/copyright).",
        collection=COLLECTION_OSM,
        source_url="https://www.openstreetmap.org/copyright",
        license_confirmed=True,
        license_checked="2026-06-24",
        extra={
            "geofabrik_pbf": "https://download.geofabrik.de/africa/cameroon-latest.osm.pbf",
            "osm_layer": "multipolygons",
            "where": "landuse IS NOT NULL OR \"natural\" IS NOT NULL",
            "table": "landuse",
        },
    ),
    Layer(
        id="health-facilities",
        title="Health facilities (healthsites.io)",
        theme="health",
        datatype="vector",
        license="ODbL-1.0",
        attribution="Health facilities: healthsites.io, © OpenStreetMap contributors, ODbL.",
        collection=COLLECTION_OSM,
        source_url="https://healthsites.io/",
        license_confirmed=True,
        license_checked="2026-06-25",
        extra={
            "hdx_geojson": "https://data.humdata.org/dataset/e4ef8126-9d18-48b1-8063-80e924ebbd9f/resource/1944baad-16af-4bd0-8411-15309bb5472d/download/cameroon.geojson",
            "table": "health_facilities",
        },
    ),
    # ---- Wave 3: rasters (each carries its own titiler render hint) ----
    Layer(
        id="copernicus-dem",
        title="Copernicus DEM GLO-30 (elevation)",
        theme="elevation",
        datatype="raster",
        license="copernicus-dem-eula",
        attribution=(
            "Elevation: Copernicus DEM GLO-30 © DLR / Airbus, provided under "
            "COPERNICUS by the European Union and ESA."
        ),
        collection=COLLECTION_OPEN,
        source_url="https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM",
        license_confirmed=True,
        license_checked="2026-06-25",
        extra={"render": "rescale=0,4000&colormap_name=terrain"},
    ),
    Layer(
        id="dem-hillshade",
        title="Hillshade (from Copernicus DEM)",
        theme="topographic",
        datatype="raster",
        license="copernicus-dem-eula",
        attribution=(
            "Hillshade derived from Copernicus DEM GLO-30 © DLR / Airbus, "
            "provided under COPERNICUS by the European Union and ESA."
        ),
        collection=COLLECTION_OPEN,
        source_url="https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM",
        license_confirmed=True,
        license_checked="2026-06-25",
        # derived from the copernicus-dem COG (must be ingested first)
        extra={"from_cog": "copernicus-dem", "render": "rescale=0,255"},
    ),
    Layer(
        id="hansen-forest",
        title="Forest cover 2000 (Hansen Global Forest Change)",
        theme="forest",
        datatype="raster",
        license="CC-BY-4.0",
        attribution="Forest cover: Hansen/UMD/Google/USGS/NASA, CC-BY 4.0.",
        collection=COLLECTION_OPEN,
        source_url="https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/download.html",
        license_confirmed=True,
        license_checked="2026-06-25",
        extra={
            "tile_urls": [
                "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_treecover2000_10N_000E.tif",
                "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_treecover2000_10N_010E.tif",
                "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_treecover2000_20N_000E.tif",
                "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_treecover2000_20N_010E.tif",
            ],
            "nodata": None,
            "render": "rescale=0,100&colormap_name=greens",
        },
    ),
    Layer(
        id="jrc-water",
        title="Surface water occurrence (JRC Global Surface Water)",
        theme="water",
        datatype="raster",
        license="copernicus-free-open",
        attribution="Surface water: EC JRC / Google — Global Surface Water, free and open.",
        collection=COLLECTION_OPEN,
        source_url="https://global-surface-water.appspot.com/download",
        license_confirmed=True,
        license_checked="2026-06-25",
        extra={
            "tile_urls": [
                "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_0E_10Nv1_4_2021.tif",
                "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_10E_10Nv1_4_2021.tif",
                "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_0E_20Nv1_4_2021.tif",
                "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_10E_20Nv1_4_2021.tif",
            ],
            "nodata": 255,
            "render": "rescale=0,100&colormap_name=blues",
        },
    ),
]

LAYERS_BY_ID: dict[str, Layer] = {layer.id: layer for layer in LAYERS}

# Map the ``--layer <name>`` CLI alias to the canonical layer id.
LAYER_ALIASES: dict[str, str] = {
    "srtm": "srtm-30m-dem",
    "sentinel2": "sentinel2-mosaic",
    "worldcover": "esa-worldcover-10m",
    "boundaries": "admin-boundaries",
    "admin": "admin-boundaries",
    "worldpop": "worldpop-population",
    "osm_roads": "osm-roads",
    "osm": "osm-roads",
    "places": "ne-populated-places",
    "rivers": "ne-rivers",
    "lakes": "ne-lakes",
    "waterways": "osm-waterways",
    "landuse": "osm-landuse",
    "health": "health-facilities",
    "dem": "copernicus-dem",
    "copdem": "copernicus-dem",
    "hillshade": "dem-hillshade",
    "forest": "hansen-forest",
    "hansen": "hansen-forest",
    "jrc": "jrc-water",
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
