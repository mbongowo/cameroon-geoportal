-- Runs once on first DB initialization (mounted into docker-entrypoint-initdb.d).
-- Enables PostGIS. The pgSTAC catalog schema is installed in Phase 2/3 via a
-- dedicated migration (pypgstac) so its version is pinned and reproducible.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Dedicated schema for portal vector layers (geoBoundaries, OSM roads, ...).
CREATE SCHEMA IF NOT EXISTS layers;

-- Separate, clearly-labeled schema for ODbL (OpenStreetMap) data so share-alike
-- never contaminates other products.
CREATE SCHEMA IF NOT EXISTS osm_odbl;

COMMENT ON SCHEMA osm_odbl IS 'OpenStreetMap-derived data. ODbL share-alike. Keep isolated.';
