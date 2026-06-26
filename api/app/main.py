"""Cameroon Geoportal API — entrypoint.

Phase 1 ships a bootable skeleton: health check + placeholder routers for
/search and /export. Real STAC search and AOI export land in Phase 3.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.routers import catalog, export, sentinel

app = FastAPI(
    title="Cameroon Geospatial Data Portal API",
    version=__version__,
    description=(
        "Search license-clear geospatial data for Cameroon and export "
        "area-of-interest clips. Every dataset carries a license + attribution."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(export.router)
app.include_router(sentinel.router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "Cameroon Geospatial Data Portal API",
        "version": __version__,
        "docs": "/docs",
        "licensing": "Only Public Domain/CC0, CC-BY 4.0, and ODbL data is served.",
    }


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
