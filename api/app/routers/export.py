"""AOI export router (skeleton).

Phase 1: validates the request shape and returns a stub. Phase 3 enqueues a
Celery task that clips the layer to the AOI, packages the chosen format with
LICENSE.txt + ATTRIBUTION.txt, and returns a signed download URL.
"""
from __future__ import annotations

from enum import Enum

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/export", tags=["export"])


class ExportFormat(str, Enum):
    geotiff = "geotiff"
    geojson = "geojson"
    geopackage = "geopackage"


class ExportRequest(BaseModel):
    layer_id: str = Field(..., examples=["srtm-30m-dem"])
    aoi: dict = Field(..., description="GeoJSON geometry (Polygon/MultiPolygon) of the area of interest")
    format: ExportFormat = ExportFormat.geotiff


@router.post("")
def create_export(req: ExportRequest) -> dict:
    """Accept an AOI export request (stub — processing wired in Phase 3)."""
    return {
        "status": "accepted",
        "detail": "Export processing is implemented in Phase 3.",
        "request": req.model_dump(),
        "note": "Every export will bundle LICENSE.txt and ATTRIBUTION.txt.",
    }
