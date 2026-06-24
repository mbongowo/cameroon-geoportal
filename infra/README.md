# infra/

Infrastructure configuration for the local Docker Compose stack.

- `postgis/init/` — SQL run once on first DB boot (enables PostGIS, creates the
  `layers` and isolated `osm_odbl` schemas).
- `titiler/` — TiTiler config (raster tiling/clipping of COGs). Defaults set via
  environment in `docker-compose.yml`.
- `martin/` — Martin config (vector tiles from PostGIS). Auto-discovers spatial
  tables; an explicit `config.yaml` can be added here when publishing curated
  layer sources.

Service ports (override via `.env`): API 8000, TiTiler 8001, Martin 3000,
frontend 5173, PostGIS 5432, Redis 6379.
