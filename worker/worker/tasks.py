"""Celery tasks.

Phase 1: a health task proving the worker runs. Phase 3 adds `clip_export`
(AOI clip → format conversion → bundle LICENSE.txt/ATTRIBUTION.txt → signed URL).
"""
from __future__ import annotations

from worker.celery_app import celery_app


@celery_app.task(name="worker.ping")
def ping() -> str:
    """Liveness probe for the worker."""
    return "pong"
