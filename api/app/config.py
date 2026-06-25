"""Application settings, loaded from environment (.env)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    api_cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Database / catalog
    database_url: str = "postgresql://geoportal:change_me_local_dev@db:5432/geoportal"
    pgstac_dsn: str = "postgresql://geoportal:change_me_local_dev@db:5432/geoportal"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # Tile services — browser-facing base URLs the API hands to the frontend.
    titiler_public_url: str = "http://localhost:8001"
    martin_public_url: str = "http://localhost:3000"

    # Where the worker writes export bundles (shared `exports` volume).
    exports_bundle_dir: str = "/exports/bundles"

    # Object storage (Cloudflare R2)
    r2_endpoint_url: str = ""
    r2_bucket: str = "cameroon-geoportal-cogs"
    r2_public_base_url: str = ""

    # Auth (Phase 5)
    jwt_secret: str = "change_me_generate_a_long_random_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


settings = Settings()
