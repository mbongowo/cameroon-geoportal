"""AOI export router.

Phase 3: enqueues a Celery job that clips the layer to the area of interest,
converts to the chosen format, and bundles LICENSE.txt + ATTRIBUTION.txt. The
bundle is served back through ``/download/{token}``.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.tasks import celery_client

router = APIRouter(tags=["export"])


class ExportFormat(str, Enum):
    geotiff = "geotiff"
    geojson = "geojson"
    geopackage = "geopackage"


class ExportRequest(BaseModel):
    layer_id: str = Field(..., examples=["worldpop-population"])
    aoi: dict = Field(..., description="GeoJSON geometry (Polygon/MultiPolygon) of the area of interest")
    format: ExportFormat = ExportFormat.geotiff


@router.post("/export")
def create_export(req: ExportRequest) -> dict:
    """Enqueue an AOI export. Returns a task id to poll at /export/{task_id}."""
    task = celery_client.send_task(
        "worker.clip_export",
        args=[req.layer_id, req.aoi, req.format.value],
    )
    return {
        "status": "accepted",
        "task_id": task.id,
        "status_path": f"/export/{task.id}",
        "note": "Every export bundles LICENSE.txt and ATTRIBUTION.txt.",
    }


@router.get("/export/{task_id}")
def export_status(task_id: str) -> dict:
    """Poll an export job. When finished, includes the download path."""
    result = AsyncResult(task_id, app=celery_client)
    state = result.state
    if state == "SUCCESS":
        return {"task_id": task_id, "state": state, "result": result.result}
    if state == "FAILURE":
        return {"task_id": task_id, "state": state, "error": str(result.result)}
    return {"task_id": task_id, "state": state}


@router.get("/download/{token}")
def download(token: str) -> FileResponse:
    """Stream a finished export bundle (zip with data + LICENSE + ATTRIBUTION)."""
    if not token.isalnum():  # tokens are uuid4 hex — reject path-traversal attempts
        raise HTTPException(status_code=400, detail="invalid token")
    bundle = Path(settings.exports_bundle_dir) / f"{token}.zip"
    if not bundle.is_file():
        raise HTTPException(status_code=404, detail="bundle not found or expired")
    return FileResponse(
        path=str(bundle),
        media_type="application/zip",
        filename=f"cameroon-geoportal-{token[:8]}.zip",
    )
