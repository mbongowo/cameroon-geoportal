"""License texts bundled into every export.

The portal charges a cost-recovery fee for hosting/curation, never for the data
rights — so each download must carry the dataset's license and attribution. This
maps each allowed license id to a short, accurate notice + canonical link.
"""
from __future__ import annotations

LICENSE_TEXTS: dict[str, str] = {
    "public-domain": (
        "PUBLIC DOMAIN\n"
        "This dataset is in the public domain (no copyright). It is openly shared "
        "without restriction on use, sale, or redistribution.\n"
    ),
    "copernicus-free-open": (
        "COPERNICUS — FREE, FULL AND OPEN\n"
        "Contains modified Copernicus Sentinel data. Access and use is free, full "
        "and open under the Legal Notice on the use of Copernicus Sentinel Data:\n"
        "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice\n"
    ),
    "CC-BY-4.0": (
        "CREATIVE COMMONS ATTRIBUTION 4.0 INTERNATIONAL (CC-BY 4.0)\n"
        "You are free to share and adapt this material for any purpose, including "
        "commercially, provided you give appropriate credit (see ATTRIBUTION.txt).\n"
        "Full licence: https://creativecommons.org/licenses/by/4.0/\n"
    ),
    "ODbL-1.0": (
        "OPEN DATA COMMONS OPEN DATABASE LICENSE (ODbL) v1.0\n"
        "You are free to copy, distribute, use, and adapt this data, provided you "
        "attribute OpenStreetMap and its contributors (see ATTRIBUTION.txt) AND "
        "keep any adapted database under the same ODbL terms (share-alike).\n"
        "Full licence: https://opendatacommons.org/licenses/odbl/1-0/\n"
    ),
}


def license_text(license_id: str) -> str:
    """Return the bundled licence notice for a license id (or a safe fallback)."""
    return LICENSE_TEXTS.get(
        license_id,
        f"LICENSE: {license_id}\nSee the dataset's source for full licence terms.\n",
    )
