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
| 4 | **OCHA COD-AB ADM0–ADM3** (replaced geoBoundaries — those levels did not nest) | Admin boundaries | Vector (PostGIS) | CC-BY-IGO 3.0 | "Administrative boundaries: OCHA / Institut National de Cartographie (INC), Cameroon — COD-AB, CC-BY-IGO 3.0." | open |
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
| ~~geoBoundaries~~ → **OCHA COD-AB** | https://data.humdata.org/dataset/cod-ab-cmr (HDX CKAN API) | ✅ CC-BY-IGO 3.0 — commercial use + redistribution OK with attribution. Source: OCHA / INC Cameroon. Replaced geoBoundaries gbOpen, whose ADM0–3 did not nest; COD-AB ADM3 dissolved up to ADM2/1/0 for guaranteed nesting | 2026-06-25 | Claude (subagent live API verify) |
| WorldPop | https://hub.worldpop.org/data/licence.txt | ✅ CC-BY 4.0 ("WorldPop datasets are licensed under the Creative Commons Attribution 4.0 International License") | 2026-06-24 | Claude (live WebFetch) |
| OSM roads | https://www.openstreetmap.org/copyright | ✅ ODbL 1.0 — share-alike; "free to copy, distribute, transmit and adapt … as long as you credit OpenStreetMap and its contributors" | 2026-06-24 | Claude (live WebFetch) |
| Natural Earth (places, rivers, lakes) | https://www.naturalearthdata.com/about/terms-of-use/ | ✅ Public Domain — "All versions of Natural Earth raster + vector map data … are in the public domain" | 2026-06-25 | Claude (live WebFetch) |
| OSM waterways + land use | https://www.openstreetmap.org/copyright | ✅ ODbL 1.0 (Geofabrik Cameroon extract → isolated osm_odbl tier) | 2026-06-24 | Claude (live WebFetch) |
| healthsites.io health facilities | https://healthsites.io/ (HDX CKAN API) | ✅ ODbL 1.0 (OSM-derived → osm_odbl tier) | 2026-06-25 | Claude (subagent API verify) |
| Copernicus DEM GLO-30 | https://dataspace.copernicus.eu/.../COP-DEM | ✅ ESA Copernicus DEM EULA — free worldwide, commercial use + redistribution OK with attribution (© DLR/Airbus, COPERNICUS/EU/ESA) | 2026-06-25 | Claude (subagent verify) |
| Hansen Global Forest Change | https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/download.html | ✅ CC-BY 4.0 ("free to copy, redistribute … even commercially"; cite Hansen/UMD/Google/USGS/NASA) | 2026-06-25 | Claude (subagent verify) |
| JRC Global Surface Water | https://global-surface-water.appspot.com/download | ✅ Copernicus free & open — "provided free of charge, without restriction of use" (EC JRC/Google) | 2026-06-25 | Claude (subagent verify) |

## How attribution flows end-to-end

1. **Catalog** — `license` + `attribution` are required fields on every STAC item.
2. **UI** — a license badge + copy-ready attribution string shows on each layer.
3. **Download** — every export bundles `LICENSE.txt` and `ATTRIBUTION.txt`.
