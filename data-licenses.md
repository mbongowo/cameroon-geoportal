# Data Licenses & Attribution

> **Foundational rule of this project:** the portal redistributes data and charges a
> cost-recovery fee, so **every dataset must have a `license` and an `attribution`
> field in the catalog — no exceptions.** Only Public Domain / CC0, CC-BY 4.0, and
> ODbL data may be ingested. The fee covers hosting, bandwidth, and curation —
> never the data rights, which remain open.

## ✅ Allowed license types

| License | Redistribute | Charge a fee | Attribution required | Share-alike |
|---|---|---|---|---|
| Public Domain / CC0 | Yes | Yes | No | No |
| CC-BY 4.0 | Yes | Yes | **Yes** | No |
| ODbL (OpenStreetMap) | Yes | Yes | **Yes** | **Yes** — keep isolated |

**ODbL handling:** OSM-derived layers live in a **separate, clearly ODbL-labeled
tier** (own STAC collection `osm-odbl`). They are never merged into other datasets,
so share-alike never contaminates other products.

## ❌ Never ingest (incompatible with redistribution / paid use)

| Dataset | Reason |
|---|---|
| **GADM** | License prohibits commercial use / redistribution without permission |
| **FAO GAUL** | Restricted redistribution terms |
| **DIVA-GIS boundaries** | Largely GADM-derived; inherits the restriction |
| **Any CC-BY-NC layer** | Non-commercial clause blocks paid use |
| **INC / Cameroon national-agency proprietary data** | Requires written licensing |

> **Substitution:** where GADM would be used for administrative boundaries, use
> **geoBoundaries (CC-BY 4.0)** instead.

## MVP layers (six, all clipped to Cameroon's national boundary)

| # | Layer | Theme | Type | License | Attribution string | Tier |
|---|---|---|---|---|---|---|
| 1 | **SRTM 30 m DEM** | Elevation | Raster (COG) | Public Domain | "Elevation data: NASA SRTM (public domain)." | open |
| 2 | **Sentinel-2 cloud-free mosaic** | Optical imagery | Raster (COG) | Copernicus (free & open) | "Contains modified Copernicus Sentinel-2 data [year], processed for the Cameroon Geoportal." | open |
| 3 | **ESA WorldCover 10 m** | Land cover | Raster (COG) | CC-BY 4.0 | "© ESA WorldCover project / Contains modified Copernicus Sentinel data (2021), licensed under CC-BY 4.0." | open |
| 4 | **geoBoundaries ADM0–ADM3** | Admin boundaries | Vector (PostGIS) | CC-BY 4.0 | "Administrative boundaries: geoBoundaries (www.geoboundaries.org), CC-BY 4.0." | open |
| 5 | **WorldPop** | Population | Raster (COG) | CC-BY 4.0 | "Population data: WorldPop (www.worldpop.org), University of Southampton, CC-BY 4.0." | open |
| 6 | **OpenStreetMap roads** | Transport | Vector (PostGIS) | **ODbL** | "© OpenStreetMap contributors, ODbL (www.openstreetmap.org/copyright)." | **osm-odbl** |

## Verification log

Every dataset's license **must be confirmed with a live fetch of the source's
license page before ingestion** (Phase 2). The result is recorded here:

| Layer | Source URL | License confirmed | Date checked | Checked by |
|---|---|---|---|---|
| SRTM 30 m DEM | https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl1-003 | ✅ Public domain — "openly shared, without restriction, in accordance with the EOSDIS Data Use and Citation Guidance" | 2026-06-24 | Claude (live WebFetch) |
| Sentinel-2 | https://dataspace.copernicus.eu/terms-and-conditions | ✅ "free, full and open" (Copernicus Sentinel Data Legal Notice) | 2026-06-24 | Claude (live WebFetch) |
| ESA WorldCover | https://esa-worldcover.org/en/data-access | ✅ CC-BY 4.0 | 2026-06-24 | Claude (live WebFetch) |
| geoBoundaries | https://www.geoboundaries.org | ✅ CC-BY 4.0 ("permits commercial and non-commercial uses with attribution") | 2026-06-24 | Claude (live WebFetch) |
| WorldPop | https://hub.worldpop.org/data/licence.txt | ✅ CC-BY 4.0 ("WorldPop datasets are licensed under the Creative Commons Attribution 4.0 International License") | 2026-06-24 | Claude (live WebFetch) |
| OSM roads | https://www.openstreetmap.org/copyright | ✅ ODbL 1.0 — share-alike; "free to copy, distribute, transmit and adapt … as long as you credit OpenStreetMap and its contributors" | 2026-06-24 | Claude (live WebFetch) |

## How attribution flows end-to-end

1. **Catalog** — `license` + `attribution` are required fields on every STAC item.
2. **UI** — a license badge + copy-ready attribution string shows on each layer.
3. **Download** — every export bundles `LICENSE.txt` and `ATTRIBUTION.txt`.
